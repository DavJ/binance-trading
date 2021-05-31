from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import numpy as np
import math

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager,
                                    round_down, round_up, format_to_precision)

class Order:

    def __init__(self, side=None, currency=None, amount=None, price=None, type='LIMIT', main_currency='BNB'):
        self.side = side
        self.currency = currency
        self.amount = amount
        self.price = round(price, 5)
        self.type = type
        self._order = None
        self._info = None
        self.main_currency = main_currency
        print(str(self))

        try:
            self.enter_order()

        except Exception as err:
            print(f'unable to enter order {self.__repr__()} reason: {err}')

    def __repr__(self):
        if self.side == 'BUY':
            return f"Order(side={self.side}, currency={self.currency}, amount={self.quantity}, price={self.buy_price}, type={self.type})"
        else:
            return f"Order(side={self.side}, currency={self.currency}, amount={self.quantity}, price={self.sell_price}, type={self.type})"

    @property
    def base_asset_precision(self):
       return self.info['baseAssetPrecision']


    @property
    def pair(self):
        return self.currency + self.main_currency

    @property
    def quantity(self):
        step_size = float([f for f in self.info['filters'] if f['filterType'] == 'LOT_SIZE'][0]['stepSize'])
        precision = - round(math.log(step_size) / math.log(10))
        return format_to_precision(round_down(self.amount, precision), self.base_asset_precision)

    @property
    def info(self):                                                                                     #cached property
        if self._info is None:
            client = get_binance_client()
            self._info = client.get_symbol_info(self.pair)
        return self._info

    @property
    def buy_price(self):
        tick_size = float([f for f in self.info['filters'] if f['filterType'] == 'PRICE_FILTER'][0]['tickSize'])
        precision = - round(math.log(tick_size) / math.log(10))
        return format_to_precision(round_down(self.price, precision), self.base_asset_precision)

    @property
    def sell_price(self):
        tick_size = float([f for f in self.info['filters'] if f['filterType'] == 'PRICE_FILTER'][0]['tickSize'])
        precision = - round(math.log(tick_size) / math.log(10))
        return format_to_precision(round_up(self.price, precision), self.base_asset_precision)

    def enter_order(self):
        client = get_binance_client()
        if self.type == 'LIMIT':

            if Decimal(self.quantity) > 0:
                if self.side == 'BUY':
                    self._order = client.order_limit_buy(symbol=self.pair, quantity=self.quantity, price=self.buy_price)
                elif self.side == 'SELL':
                    self._order = client.order_limit_sell(symbol=self.pair, quantity=self.quantity, price=self.sell_price)
                else:
                   print(f'not entering trade - unknown order side {self.side}')
            else:
                print(f'not entering trade - trade filters would result to zero quantity')
        else:
            print(f'unknown order type {self.type}')
