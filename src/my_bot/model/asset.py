# https://python-binance.readthedocs.io/en/latest/overview.html?highlight=async%20client#async-api-calls
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json
from src.my_bot.model.statistix import Statistix


from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    ilen, get_order_book_statistics)


class Asset:
    def __init__(self, currency=None, asset_amount_free=None, asset_amount_locked=None, main_currency=CONFIGURATION.MAIN_CURRENCY):
        self.currency = currency
        self.main_currency = main_currency
        self.asset_amount_free = None if asset_amount_free is None else Decimal(asset_amount_free)
        self.asset_amount_locked = None if asset_amount_locked is None else Decimal(asset_amount_locked)
        self.last_buy_price = None
        self.last_sell_price = None
        self.recent_average_buy_price = None
        self.recent_average_sell_price = None
        self._time = None
        self._id = None
        if self.currency != self.main_currency:
            self.statistix = Statistix(currency=self.currency, trade_currency=self.main_currency)
        else:
            self.statistix = None

        if asset_amount_free is None or asset_amount_locked is None:
            # get balances from Binance
            if use_async_client():
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.aio_get_balance())
            else:
                self.get_balance()

        self.update_last_trades()

        #loop_db = asyncio.get_event_loop()
        #loop_db.run_until_complete(self.__aio_link__())

    def __repr__(self):
        return f"Asset(currency='{self.currency}, asset_amount_free={self.asset_amount_free}, asset_amount_locked={self.asset_amount_locked})"

    @property
    def pair(self):
        return self.currency + self.main_currency

    async def __aio_link__(self):
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            cursor = await conn.execute(f"SELECT id FROM asset WHERE currency='{self.currency}'")
            row = await cursor.fetchone()
            # rows = await cursor.fetchall()
            await cursor.close()
            # await conn.close()     ... not
        try:
            self._id = row['id']
        except Exception:
            pass
            # await self.aio_db_insert_asset()

    async def aio_get_balance(self):
        """
        gets asset from  (async)
        """
        client = await get_async_binance_client()
        try:
            res = await client.get_asset_balance(self.currency)
            self.asset_amount_free = Decimal(res['free'])
            self.asset_amount_locked = Decimal(res['locked'])

        except Exception:
            print(f'cannot get asset info')

        finally:
            await client.close_connection()

    def get_balance(self):
        """
        gets asset from  (sync)
        """
        client = get_binance_client()
        try:
            res = client.get_asset_balance(self.currency)
            self.asset_amount_free = Decimal(res['free'])
            self.asset_amount_locked = Decimal(res['locked'])

        except Exception:
            print(f'cannot get asset info')

    def update_last_trades(self):

        def calc_average_price_for_asset_amount(asset_amount, trades):
            sorted_trades = sorted(trades, key=lambda x: x['time'], reverse=True)
            sum = 0
            weighted_sum = 0
            for trade in sorted_trades:
                remaining_amount = max(0, asset_amount - sum)
                if remaining_amount == 0:
                    break
                sum += remaining_amount
                weighted_sum += remaining_amount * Decimal(trade['price'])
            return weighted_sum / sum

        if self.currency != self.main_currency:
            client = get_binance_client()
            asset_trades = client.get_my_trades(symbol=self.currency + self.main_currency, limit=30)
            buy_trades = list(filter(lambda x: x['isBuyer'], asset_trades))
            sell_trades = list(filter(lambda x: not x['isBuyer'], asset_trades))

            try:
                last_buy_trade = sorted(buy_trades, key=lambda x: x['time'])[-1]
                self.last_buy_price = Decimal(last_buy_trade['price'])
                self.recent_average_buy_price = calc_average_price_for_asset_amount(self.asset_amount_free, buy_trades)
            except Exception:
                # set some initial values
                statistics = get_order_book_statistics(self.currency + self.main_currency)
                self.last_buy_price = statistics['avg_buy_price']
                self.recent_average_buy_price = self.last_buy_price

            try:
                last_sell_trade = sorted(sell_trades, key=lambda x: x['time'])[-1]
                self.last_sell_price = Decimal(last_sell_trade['price'])
                self.recent_average_sell_price = calc_average_price_for_asset_amount(self.asset_amount_free,
                                                                                     sell_trades)
            except Exception:
                # set some initial values
                statistics = get_order_book_statistics(self.currency + self.main_currency)
                self.last_sell_price = statistics['avg_sell_price']
                self.recent_average_sell_price = self.last_sell_price

    async def aio_db_insert_asset(self):
        insert_sql = '''
        INSERT INTO asset (currency, asset_amount_free, asset_amount_locked, last_update_time)
        VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H-%M','now')) ;
        '''
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            asset = (self.currency,
                     str(self.asset_amount_free) if self.asset_amount_free is not None else None,
                     str(self.asset_amount_locked) if self.asset_amount_locked is not None else None)
            await conn.execute(insert_sql, asset)
            await conn.commit()

    async def aio_db_update_asset(self):
        update_sql = '''
            UPDATE asset 
            SET asset_amount=?, asset_amount_available=?, last_update_time=strftime('%Y-%m-%d %H-%M','now')
            WHERE id=?;
            '''
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            asset = (str(self.asset_amount_free) if self.asset_amount_free is not None else None,
                     str(self.asset_amount_locked) if self.asset_amount_locked is not None else None,
                     self._id)
            await conn.execute(update_sql, asset)
            await conn.commit()

    def update(self, time=None, balance=None):
        self._time = time
        if balance['a'] == self.currency:
            self.asset_amount_free = Decimal(balance['f'])
            self.asset_amount_locked = Decimal(balance['l'])
            self.update_last_trades()
        else:
            raise (f'incorrect asset currency')

    @property
    def asset_amount_total(self):
        return self.asset_amount_free + self.asset_amount_locked

    @property
    def asset_amount_in_main_currency_market(self):
        if self.currency == self.main_currency:
            return self.asset_amount_total
        else:
            client = get_binance_client()
            average_market_price = Decimal(client.get_avg_price(symbol=self.pair)['price'])
            return (self.asset_amount_free + self.asset_amount_locked) * average_market_price
