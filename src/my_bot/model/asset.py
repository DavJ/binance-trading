# https://python-binance.readthedocs.io/en/latest/overview.html?highlight=async%20client#async-api-calls
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json

from src.my_bot.basic_tools import CONFIGURATION, get_binance_client, get_async_binance_client, use_async_client


class Asset:
    def __init__(self, currency=None, asset_amount_free=None, asset_amount_locked=None, main_currency='BNB'):
        self.currency = currency
        self.main_currency = main_currency
        self.asset_amount_free = asset_amount_free
        self.asset_amount_locked = asset_amount_locked
        self.last_buy_price = None
        self.last_sell_price = None
        self._time = None
        self._id = None

        if asset_amount_free is None or asset_amount_locked is None:
            #get balances from Binance
            if use_async_client():
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.aio_get_balance())
            else:
                self.get_balance()

            self.update_last_trades()

        loop_db = asyncio.get_event_loop()
        loop_db.run_until_complete(self.__aio_link__())

    def __repr__(self):
       return f"Asset(currency='{self.currency}, asset_amount_free={self.asset_amount_free}, asset_amount_locked={self.asset_amount_locked})"

    async def __aio_link__(self):
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            cursor = await conn.execute(f"SELECT id FROM asset WHERE currency='{self.currency}'")
            row = await cursor.fetchone()
            #rows = await cursor.fetchall()
            await cursor.close()
            #await conn.close()     ... not
        try:
            self._id = row['id']
        except Exception:
             pass
             #await self.aio_db_insert_asset()

    async def aio_get_balance(self):
        """
        gets asset from  (async)
        """
        client = await get_async_binance_client()
        try:
            res = await client.get_asset_balance(self.currency)
            self.asset_amount_free = float(res['free'])
            self.asset_amount_locked = float(res['locked'])

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
            self.asset_amount_free = float(res['free'])
            self.asset_amount_locked = float(res['locked'])

        except Exception:
            print(f'cannot get asset info')

    def update_last_trades(self):
        if self.currency != self.main_currency:
            client = get_binance_client()
            asset_trades = client.get_my_trades(symbol=self.currency + self.main_currency, limit=30)
            last_buy_trade = sorted(filter(lambda x: x['isBuyer'], asset_trades), key=lambda x: x['time'])[-1]
            last_sell_trade = sorted(filter(lambda x: not x['isBuyer'], asset_trades), key=lambda x: x['time'])[-1]
            self.last_buy_price = float(last_buy_trade['price'])
            self.last_sell_price = float(last_sell_trade['price'])

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
            self.asset_amount_free = balance['f']
            self.asset_amount_locked = balance['l']
            self.update_last_trades()
        else:
            raise(f'incorrect asset currency')
