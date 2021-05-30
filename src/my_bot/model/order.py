from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import numpy as np

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager,
                                    round_down)

class Order:

    def __init__(self, side=None, currency=None, amount=None, price=None, type='LIMIT', main_currency='BNB'):
        self.side = side
        self.currency = currency
        self.amount = amount
        self.price = round(price, 5)
        self.type = type
        self._order = None
        self.main_currency = main_currency
        print(str(self))

        try:
            self.enter_order()

        except Exception as err:
            print(f'unable to enter order {self.__repr__()} reason: {err}')

    def __repr__(self):
        return f"Order(side={self.side}, currency={self.currency}, amount={self.amount}, price={self.price}. type={self.type})"

    @property
    def pair(self):
       return self.currency + self.main_currency

    def enter_order(self):
        client = get_binance_client()
        if self.type == 'LIMIT':
            if self.side == 'BUY':
                order = client.order_limit_buy(symbol=self.pair, quantity=round_down(self.amount, 1), price=round(self.price, 5))
            elif self.side == 'SELL':
                order = client.order_limit_sell(symbol=self.pair, quantity=round_down(self.amount, 1), price=round(self.price, 5))
            else:
                print(f'unknown order side {self.side}')
        else:
            print(f'unknown order type {self.type}')



