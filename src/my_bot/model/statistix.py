from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import aiosqlite
import json
import numpy as np
import itertools
import operator

from binance import Client
from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)


class Statistix:

    def __init__(self, currency=None, main_currency='BNB'):
        self.currency = currency
        self.main_currency = main_currency
        self.average_price = None
        self.max_price = None
        self.min_price = None
        self.average_volume = None
        self.daily_changer = None

        # self.previous_time = time.time() if time is None else time

        self.update()

    def __repr__(self):
        return f"Statistix(time={self.previous_time}, last_price={self.last_price}, last_volume={self.last_volume}, n_dim={self.n_dim})"

    def update(self):
        client = get_binance_client()
        # ['Opened','High','Low','Close','Volume','Closed']
        klines = client.get_historical_klines(self.pair, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
        prices = [Decimal(kline[3]) for kline in klines]

        self.average_price = sum(prices) / len(prices)
        self.max_price = max([Decimal(kline[1]) for kline in klines])
        self.min_price = min([Decimal(kline[2]) for kline in klines])

        changer = client.get_ticker(symbol=self.pair)
        self.daily_changer = Decimal(changer['priceChangePercent'])
        self.last_price = Decimal(changer['lastPrice'])

    @property
    def pair(self):
        return self.currency + self.main_currency

    @property
    def daily_changer_eligible_for_buy(self):
        return self.daily_changer < Decimal(CONFIGURATION.BUY_DAILY_CHANGER)

    @property
    def daily_changer_eligible_for_sell(self):
        return self.daily_changer > Decimal(CONFIGURATION.SELL_DAILY_CHANGER)

    def price_eligible_for_buy(self, low_ratio='0.04', high_ratio='0.33'):
        self.update()
        min_eligible_price = Decimal(low_ratio) * self.max_price + (1 - Decimal(low_ratio)) * self.min_price
        max_eligible_price = Decimal(high_ratio) * self.max_price + (1 - Decimal(high_ratio)) * self.min_price

        return min_eligible_price < self.last_price < max_eligible_price

    def price_eligible_for_sell(self, low_ratio='0.67', high_ratio='0.93'):
        self.update()
        min_eligible_price = Decimal(low_ratio) * self.max_price + (1 - Decimal(low_ratio)) * self.min_price
        max_eligible_price = Decimal(high_ratio) * self.max_price + (1 - Decimal(high_ratio)) * self.min_price

        return min_eligible_price < self.last_price < max_eligible_price

    def eligible_for_buy(self):
        self.update()
        return self.price_eligible_for_buy() and self.daily_changer_eligible_for_buy
        # return self.daily_changer_eligible_for_buy

    def eligible_for_sell(self):
        if CONFIGURATION.SELL_IMMEDIATELY:
            return True
        else:
            self.update()
            return self.price_eligible_for_sell() and self.daily_changer_eligible_for_sell
