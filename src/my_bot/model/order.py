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
                                    round_down, round_up, format_to_precision,
                                    get_average_buy_price_for_sell_quantity, get_average_sell_price_for_buy_quantity)
from src.my_bot.model.profit import Profit


class Order:

    def __init__(self, side=None, currency=None, amount=None, limit_price=None, type='LIMIT', main_currency='BNB'):
        """

        :param side:
        :param currency:
        :param amount:
        :param price:                   ...                       if not provided profitable price is used (recommended)
        :param type:
        :param main_currency:
        :param profit:
        """

        self.side = side
        self.currency = currency
        self.amount = amount

        self.type = type
        self._order = None
        self._info = None
        self.main_currency = main_currency
        self.profit = Profit()
        self.limit_price = limit_price


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
                    if self.average_sell_price_for_buy_trade > self.price:
                        self._order = client.order_limit_buy(symbol=self.pair, quantity=self.quantity, price=self.buy_price)
                elif self.side == 'SELL':
                    if self.average_buy_price_for_sell_trade < self.price:
                        self._order = client.order_limit_sell(symbol=self.pair, quantity=self.quantity, price=self.sell_price)
                else:
                   print(f'not entering trade - unknown order side {self.side}')
            else:
                print(f'not entering trade - trade filters would result to zero quantity')
        else:
            print(f'unknown order type {self.type}')

    @property
    def average_buy_price_for_sell_trade(self):
        return get_average_buy_price_for_sell_quantity(trade_quantity=self.quantity,
                                                       currency=self.currency,
                                                       main_currency=self.main_currency)

    @property
    def average_sell_price_for_buy_trade(self):
        return get_average_sell_price_for_buy_quantity(trade_quantity=self.quantity, currency=self.currency,
                                                       main_currency=self.main_currency)

    @property
    def profitable_price(self):
        if self.side == 'BUY':
            return self.profit.profitable_buy_price_for_previous_sell_price(self.average_sell_price_for_buy_trade)
        elif self.side == 'SELL':
            return self.profit.profitable_sell_price_for_previous_buy_price(self.average_buy_price_for_sell_trade)
        else:
            raise(f'unsupported side {self.side}')

    @property
    def price(self):
        if self.side == 'BUY':
            return min(self.limit_price, self.profitable_price)
        elif self.side == 'SELL':
            buy_strategy = min(max(0, Decimal(CONFIGURATION.SELL_STRATEGY)), 1)           #must be 0-1, 1 for max profit
            strategical_selling_price = ()
            return max(self.limit_price, self.profitable_price)
        else:
            raise(f'unsupported side {self.side}')
