from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import inspect

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)
from src.my_bot.model.kalman import Kalman
from src.my_bot.model.chart import Chart


class OrderBook:
    #ticker https://python-binance.readthedocs.io/en/latest/websockets.html
    def __init__(self, currency=None, asset_currency='BNB'):
        self.currency = currency
        self.asset_currency = asset_currency
        self.pair = currency + asset_currency
        self.time = None
        self._bids = None
        self._asks = None
        self.min_buy_price = None  # !
        self.max_buy_price = None
        self.avg_buy_price = None
        self.total_ask = None
        self.min_sell_price = None
        self.max_sell_price = None  # !
        self.avg_sell_price = None
        self.total_bid = None
        self.avg_price_difference = None
        self.avg_price_relative_difference = None
        self.max_price_difference = None
        self.max_price_relative_difference = None
        self.update()

    def __repr__(self):
        return f"OrderBook(currency='{self.currency}, asset_currency={self.asset_currency})"

    def update(self):
        client = get_binance_client()
        ticker = client.get_order_book(symbol=self.pair)
        self._bids = ticker['bids']
        self._asks = ticker['asks']
        self.min_buy_price = min([float(bid[0]) for bid in self._bids])
        self.max_buy_price = max([float(bid[0]) for bid in self._bids])
        self.total_bid = sum([float(bid[1]) for bid in self._bids])
        self.avg_buy_price = sum([float(bid[0]) * float(bid[1]) for bid in self._bids]) / self.total_bid
        self.min_sell_price = min([float(ask[0]) for ask in self._asks])
        self.max_sell_price = max([float(ask[0]) for ask in self._asks])
        self.total_ask = sum([float(ask[1]) for ask in self._asks])
        self.avg_sell_price = sum([float(ask[0]) * float(ask[1]) for ask in self._asks]) / self.total_ask
        self.avg_price_difference = self.avg_sell_price - self.avg_buy_price
        self.avg_price_relative_difference = 2* self.avg_price_difference / (self.avg_sell_price + self.avg_buy_price)
        self.max_price_difference = self.max_sell_price - self.max_buy_price
        self.max_price_relative_difference = 2 * self.max_price_difference / (self.max_sell_price + self.max_buy_price)

    def print(self):
        print(f'ORDER BOOK for {self.pair}')
        for i in inspect.getmembers(self):

            # to remove private and protected
            # functions
            if not i[0].startswith('_'):

                # To remove other methods that
                # does not start with a underscore
                if not inspect.ismethod(i[1]):
                    print(f'{i[0]} : {i[1]}')