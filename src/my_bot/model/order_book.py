from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import inspect

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager,
                                    get_order_book_statistics)
from src.my_bot.model.kalman import Kalman
from src.my_bot.model.chart import Chart


class OrderBook:
    #ticker https://python-binance.readthedocs.io/en/latest/websockets.html
    def __init__(self, currency=None, main_currency='BNB'):
        self.currency = currency
        self.asset_currency = main_currency
        self.pair = currency + main_currency
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
        statistics = get_order_book_statistics(self.pair)
        for item in statistics:
            setattr(self, item, statistics[item])

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