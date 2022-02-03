import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
#os.environ['CUDA_VISIBLE_DEVICES'] = '0'
#os.environ["SM_FRAMEWORK"] = "tf.keras"
import asyncio
import numpy as np
from decimal import Decimal
from basic_tools import (get_binance_client, CONFIGURATION, get_trading_currencies,
                         round_down, TRADING_PAIRS, TRADING_CURRENCIES, cancel_obsolete_orders,
                         get_average_buy_price_for_sell_quantity, get_average_sell_price_for_buy_quantity)
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.statistix import Statistix
from model.user_ticker import UserTicker
from model.order import Order
from model.profit import Profit
from time import sleep
from datetime import datetime
import math
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Conv2D, Flatten, Dense, LSTM, Embedding


from basic_tools import get_main_currency_pairs, get_close_price, normalize_rate, get_relative_close_price


class WindowGenerator():
  def __init__(self, input_width, label_width, shift,
               train_df=None, val_df=None, test_df=None,
               label_columns=None):
    # Store the raw data.
    self.train_df = train_df
    self.val_df = val_df
    self.test_df = test_df

    # Work out the label column indices.
    self.label_columns = label_columns
    if label_columns is not None:
      self.label_columns_indices = {name: i for i, name in
                                    enumerate(label_columns)}
    self.column_indices = {name: i for i, name in
                           enumerate(train_df.columns)}

    # Work out the window parameters.
    self.input_width = input_width
    self.label_width = label_width
    self.shift = shift

    self.total_window_size = input_width + shift

    self.input_slice = slice(0, input_width)
    self.input_indices = np.arange(self.total_window_size)[self.input_slice]

    self.label_start = self.total_window_size - self.label_width
    self.labels_slice = slice(self.label_start, None)
    self.label_indices = np.arange(self.total_window_size)[self.labels_slice]

  def __repr__(self):
    return '\n'.join([
        f'Total window size: {self.total_window_size}',
        f'Input indices: {self.input_indices}',
        f'Label indices: {self.label_indices}',
        f'Label column name(s): {self.label_columns}'])


class Brain:

    def __init__(self, units=64):

        self.N = 6     #2^N is number of samples for prediction
        self.M = 2     #2^M is number of samples to predict
        self.IN_STEPS = 2 ** self.N
        self.OUT_STEPS = 2 ** self.M
        self.units = units
        self.pairs = get_main_currency_pairs()
        self.num_pairs = len(self.pairs)
        self.window = None
        self.train_data = None
        self.history = None

        self.refresh_train_data()

    def refresh_train_data(self):
        def pair_symbol(pair):
            return pair[0] + pair[1]

        relative_close_prices = {}

        for pair in self.pairs:
            rcp = get_relative_close_price(pair)
            relative_close_prices.update(**{pair_symbol(pair): rcp})

        all_data = []
        length_of_data = len(rcp)
        for index in range(length_of_data):
            all_data.append(np.array([(relative_close_prices[pair_symbol(pair)][index]-1) for pair in self.pairs]))

        #split 70%, 20%, 10%
        self.train_data = np.array(all_data[0:int(length_of_data*0.7)])
        self.validation_data = np.array(all_data[int(length_of_data*0.7): int(length_of_data*0.9)])
        self.test_data = np.array(all_data[int(length_of_data*0.9):])
        self.num_features = self.train_data.shape[1]

        self.train_mean = self.train_data.mean()
        self.train_std = self.train_data.std()

        self.normalized_train_data = (self.train_data - self.train_mean) / self.train_std
        self.normalized_validation_data = (self.validation_data - self.train_mean) / self.train_std
        self.normalized_test_data = (self.test_data - self.train_mean) / self.train_std

        self.window = WindowGenerator(input_width=self.IN_STEPS,
                                      label_width=self.OUT_STEPS,
                                      shift=self.OUT_STEPS,
                                      train_df=self.normalized_train_data,
                                      val_df=self.normalized_validation_data,
                                      test_df=self.normalized_test_data)

    def create_model(self):
        self.model = tf.keras.Sequential([
            # Shape [batch, time, features] => [batch, lstm_units].
            # Adding more `lstm_units` just overfits more quickly.
            tf.keras.layers.LSTM(self.units, return_sequences=False),
            # Shape => [batch, out_steps*features].
            tf.keras.layers.Dense(self.OUT_STEPS * self.num_features * self.num_pairs,
                                  kernel_initializer=tf.initializers.zeros()),
            # Shape => [batch, out_steps, features].
            tf.keras.layers.Reshape([self.OUT_STEPS, self.num_pairs, self.num_features])
        ])

    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, window):
        self._window = window

    def window_plot(self):
        self.window.plot()

    def compile_and_fit(self, patience=2, epochs=20):
        early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
                                                          patience=patience,
                                                          mode='min')

        self.model.compile(loss=tf.losses.MeanSquaredError(),
                           optimizer=tf.optimizers.Adam(),
                           metrics=[tf.metrics.MeanAbsoluteError()])

        self.history = self.model.fit(self.window.train, epochs=epochs,
                                 validation_data=self.window.val,
                                 callbacks=[early_stopping])

class Application:

    def __init__(self):

        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
        self.active_orders = []
        self.profit = Profit()

    def main(self):

        brain = Brain()
        brain.create_model()
        brain.window_plot()
        brain.compile_and_fit()

        while True:
            try:
                self.update()
                self.trade()
            except Exception:
                pass

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(int(CONFIGURATION.SLEEP)))

def full_stack():
    import traceback, sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        del stack[-1]       # remove call of full_stack, the printed exception
                            # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
         stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr

if __name__ == "__main__":
    #os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    application = Application()
    application.main()
