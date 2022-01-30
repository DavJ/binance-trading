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
from keras.preprocessing import sequence
from keras.models import Sequential
from keras.layers import Dense, Embedding
from keras.layers import LSTM
from keras.datasets import imdb
from basic_tools import get_main_currency_pairs, get_close_price, normalize_rate


def get_normalized_close_price_train_data_for_pair(pair):
    M, N = 5, 5   #N ... split to chunks of length 2^N, M .... predict exponent
    cp = get_normalized_close_price(pair)
    train_data = [[cp[i + k**2 - j**2] for k in range(M) for j in range(N)] for i in range(2**N, len(cp) - 2**M)]
    #train_data = [[cp[i + k ** 2 - j ** 2] for k in range(M) for j in range(N)] for i inrange(2 ** N, len(cp) - 2 ** M)]

    return np.array(train_data)


class LSTM:

    def __init__(self):

        self.N = 5     #2^N is number of samples for prediction
        self.M = 2     #2^M is number of samples to predict
        self.pairs =  get_main_currency_pairs()
        self.train_data = None

        self.refresh_train_data()

    def refresh_train_data(self):
        x_train = []
        y_train = []
        scale = 10

        for pair in self.pairs:
            cp = get_close_price(pair)
            batch_len = (2**self.N + 2**self.M)
            batch_count = len(cp) - batch_len

            x_train.append(
                np.array([normalize_rate(cp[i + c], cp[2**self.N + c], scale=scale)
                for c in range(batch_count) for i in range(0, 2 ** self.N)])
            )

            y_train.append(
                np.array([normalize_rate(cp[j + c], cp[2**self.N + c], scale=scale) for c in range(batch_count)
                 for j in range(2 ** self.N, batch_len)])
            )

        self.x_train = np.array(x_train)
        self.y_train = np.array(y_train)

    def create_model(self):
       self.model = Sequential()
       self.model.add(Embedding(2000, 128))
       self.model.add(LSTM(128, dropout=0.2, recurrent_dropout=0.2))
       self.model.add(Dense(1, activation='sigmoid'))

    def fit(self):
        self.model.fit(
           self.x_train, self.y_train,
           batch_size=1,
           epochs=15,
           #validation_data=(x_test, y_test)
        )

class Application:

    def __init__(self):

        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
        self.active_orders = []
        self.profit = Profit()

        #self.symbol_tickers = {}

        #self.assets = {currency: Asset(currency=currency) for currency in TRADING_CURRENCIES}

        #self.order_books = {curr1 + curr2: OrderBook(currency=curr1, trade_currency=curr2)
        #                    for curr1, curr2 in TRADING_PAIRS}

        #self.statistixes = {curr1 + curr2: Statistix(currency=curr1, trade_currency=curr2)
        #                    for curr1, curr2 in TRADING_PAIRS}

    def main(self):

        brain = LSTM()

        brain.create_model()
        brain.fit()

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
    application = Application()
    try:
        application.main()
    except:
        full_stack()
