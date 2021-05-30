from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
import numpy as np

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)

class Order:

    def __init__(self, side=None, currency=None, amount=None, price=None, type='LIMIT', main_currency='BNB'):
        self.side = side
        self.currency = currency
        self.amount = amount
        self.price = price
        self.type = type
        print(str(self))

    def __repr__(self):
        return f"Order(side={self.side}, currency={self.currency}, amount={self.amount}, price={self.price}. type={self.type})"




