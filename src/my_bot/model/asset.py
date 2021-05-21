#https://python-binance.readthedocs.io/en/latest/overview.html?highlight=async%20client#async-api-calls
import asyncio

import datetime
import aiosqlite
import sqlite3
import json

from basic_tools import CONFIGURATION, get_async_binance_client

class Asset():
    def __init__(self, currency=None):
        self.currency = currency
        self.asset_amount = None
        self.asset_amount_available = 0
        self.max_amount = 0

        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.get())

    async def get(self):
        """
        gets asset from binance
        """
        client = await get_async_binance_client()


    async def aio_insert_asset(currency=None, asset_amount=None, asset_amount_available=None, max_amount=None):
        insert_sql = '''
        INSERT INTO assets (currency, asset_amount_total, asset_amount_available, max_amount, last_update_time)
        VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H-%M','now')) ;
        '''
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            asset = (self.currency, self.asset_amount, self.asset_amount_available, self.max_amount)
            await conn.execute(insert_sql, asset)
            await conn.commit()
