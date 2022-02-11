'''
https://www.tensorflow.org/tutorials/structured_data/time_series
'''
import os
import asyncio
import pandas as pd
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
import matplotlib.pyplot as plt
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

  def split_window(self, features):
      inputs = features[:, self.input_slice, :]
      labels = features[:, self.labels_slice, :]
      if self.label_columns is not None:
          labels = tf.stack(
              [labels[:, :, self.column_indices[name]] for name in self.label_columns],
              axis=-1)

      # Slicing doesn't preserve static shape information, so set the shapes
      # manually. This way the `tf.data.Datasets` are easier to inspect.
      inputs.set_shape([None, self.input_width, None])
      labels.set_shape([None, self.label_width, None])

      return inputs, labels

  def make_dataset(self, data):
      data = np.array(data, dtype=np.float32)
      ds = tf.keras.utils.timeseries_dataset_from_array(
          data=data,
          targets=None,
          sequence_length=self.total_window_size,
          sequence_stride=1,
          shuffle=True,
          batch_size=32, )

      ds = ds.map(self.split_window)

      return ds

  @property
  def train(self):
      return self.make_dataset(self.train_df)

  @property
  def val(self):
      return self.make_dataset(self.val_df)

  @property
  def test(self):
      return self.make_dataset(self.test_df)

  @property
  def example(self):
      """Get and cache an example batch of `inputs, labels` for plotting."""
      result = getattr(self, '_example', None)
      if result is None:
          # No example batch was found, so get one from the `.train` dataset
          result = next(iter(self.train))
          # And cache it for next time
          self._example = result
      return result


class Brain:

    def __init__(self, units=32):

        self.N = 5     #2^N is number of samples for prediction
        self.M = 1     #2^M is number of samples to predict
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

        self.all_data = []
        length_of_data = len(rcp)
        for index in range(length_of_data):
            self.all_data.append(np.array([float(relative_close_prices[pair_symbol(pair)][index]-1) for pair in self.pairs]))

        #split 70%, 20%, 10%
        self.train_data = np.array(self.all_data[0:int(length_of_data*0.7)])
        self.validation_data = np.array(self.all_data[int(length_of_data*0.7): int(length_of_data*0.9)])
        self.test_data = np.array(self.all_data[int(length_of_data*0.9):])
        self.num_features = self.train_data.shape[1]

        self.train_mean = self.train_data.mean()
        self.train_std = self.train_data.std()

        self.normalized_train_data = (self.train_data - self.train_mean) / self.train_std
        self.normalized_validation_data = (self.validation_data - self.train_mean) / self.train_std
        self.normalized_test_data = (self.test_data - self.train_mean) / self.train_std
        #self.label_columns = [f'T+{x}' for x in range(1, self.OUT_STEPS + 1)]
        self.columns = [pair_symbol(pair) for pair in self.pairs]

        self.window = WindowGenerator(input_width=self.IN_STEPS,
                                      label_width=self.OUT_STEPS,
                                      shift=self.OUT_STEPS,
                                      train_df=self.train_df,
                                      val_df=self.validation_df,
                                      test_df=self.test_df
        )

    def create_model(self):
        num_features = 1
        input_dropout=0.4
        recurrent_dropout=0.4
        self.model = tf.keras.Sequential([
            # Shape [batch, time, features] => [batch, lstm_units].
            # Adding more `lstm_units` just overfits more quickly.
            tf.keras.layers.LSTM(self.units,
                                 return_sequences=False,
                                 dropout=input_dropout,
                                 recurrent_dropout=recurrent_dropout),
            # Shape => [batch, out_steps*features].
            tf.keras.layers.Dense(self.OUT_STEPS * num_features * self.num_pairs,
                                  kernel_initializer=tf.initializers.zeros()),
            # Shape => [batch, out_steps, features].
            #tf.keras.layers.Reshape([self.OUT_STEPS, self.num_pairs, self.num_features])
            tf.keras.layers.Reshape([self.OUT_STEPS, self.num_pairs])
        ])

    @property
    def predict(self):
        return self.model.predict(self.window.test)

    @property
    def window(self):
        return self._window

    @window.setter
    def window(self, window):
        self._window = window

    def compile_and_fit(self, patience=5, epochs=250):
        early_stopping = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
                                                          min_delta=0,
                                                          patience=patience)

        modelckpt_callback = tf.keras.callbacks.ModelCheckpoint(
            monitor="val_loss",
            filepath='./model_checkpoint',
            verbose=1,
            save_weights_only=True,
            save_best_only=True,
        )

        self.model.compile(loss=tf.losses.MeanSquaredError(),
                           optimizer=tf.optimizers.Adam(),
                           metrics=[tf.metrics.MeanAbsoluteError()],
                           run_eagerly=True)


        self.history = self.model.fit(self.window.train, epochs=epochs,
                                      verbose=1,
                                      validation_data=self.window.val,
                                      callbacks=[early_stopping, modelckpt_callback])
                                      #callbacks=[modelckpt_callback])
        self.model.summary()

    @property
    def train_df(self):
        return pd.DataFrame(self.normalized_train_data, columns=self.columns)

    @property
    def validation_df(self):
        return pd.DataFrame(self.normalized_validation_data, columns=self.columns)

    @property
    def test_df(self):
        return pd.DataFrame(self.normalized_test_data, columns=self.columns)

    def visualize_loss(self, title='loss plot'):
        loss = self.history.history["loss"]
        val_loss = self.history.history["val_loss"]
        epochs = range(len(loss))
        plt.figure()
        plt.plot(epochs, loss, "b", label="Training loss")
        plt.plot(epochs, val_loss, "r", label="Validation loss")
        plt.title(title)
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend()
        plt.show()

    def show_raw_visualization(self):
        time_data = range(len(self.all_data))
        fig, axes = plt.subplots(
            nrows=7, ncols=2, figsize=(15, 20), dpi=80, facecolor="w", edgecolor="k"
        )
        colors = ["blue", "orange", "green", "red", "purple", "brown", "pink", "gray", "olive", "cyan",
        ]

        for i in range(len(self.columns)):
            key = self.columns[i]
            c = colors[i % (len(colors))]
            t_data = pd.DataFrame([self.all_data[j][i] for j in time_data])
            t_data.index = time_data
            t_data.head()
            ax = t_data.plot(
                ax=axes[i // 2, i % 2],
                color=c,
                title="{} - {}".format(self.columns[i], key),
                rot=25,
            )
            ax.legend([self.columns[i]])
        plt.tight_layout()


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

        brain.show_raw_visualization()
        #brain.window_plot()
        brain.compile_and_fit()
        brain.visualize_loss()

        #predict = brain.predict

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
