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
    def __init__(self, currency=None, trade_currency=CONFIGURATION.MAIN_CURRENCY):
        self.currency = currency
        self.trade_currency = trade_currency
        self.pair = currency + trade_currency
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
        self.min_price_difference = None
        self.min_price_relative_difference = None
        self.avg_current_price = None
        self.avg_market_price = None
        self.update()

    def __repr__(self):
        return f"OrderBook(currency='{self.currency}, asset_currency={self.trade_currency})"

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

    @property
    def strategical_buying_price(self):
        buy_strategy = Decimal(CONFIGURATION.BUY_STRATEGY)  # must be >=0 increase for max profit
        if buy_strategy == 0:
            bs = 1
        else:
            bs = min(1, 1/buy_strategy)

        return bs * min(self.avg_current_price, self.max_buy_price)

    @property
    def strategical_selling_price(self):
        sell_strategy = Decimal(CONFIGURATION.SELL_STRATEGY)  # must be >=0 increase for max profit
        ss = max(1, sell_strategy)
        return ss * max(self.avg_current_price, self.min_sell_price)
