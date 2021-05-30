from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)
from src.my_bot.model.kalman import Kalman
from src.my_bot.model.chart import Chart
from src.my_bot.model.asset import Asset

class UserTicker:

    def __init__(self):
        self._async_client = None
        self._client = None
        self._twm = None
        self._assets = {}

        self._client =get_binance_client()
        self._account = self._client.get_account()
        for item in self._account['balances']:
            self._assets.update(**{item['asset']: Asset(currency=item['asset'], asset_amount_free=item['free'], asset_amount_locked=item['locked'])})

        if use_async_client():
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.aio_ticker_run())
        else:
            self.ticker_run()

    def __repr__(self):
       return f"UserTicker()"

    async def aio_ticker_run(self):
        bm = await get_async_web_socket_manager()
        # then start receiving messages
        us = bm.user_socket()
        async with us as uscm:
            while True:
                res = await uscm.recv()
                print(res)
                if res['e'] == 'outboundAccountPosition':
                    for balance in res['B']:
                        message_time = datetime.datetime.fromtimestamp(int(msg['E']) / 1000)
                        self._assets[balance['a'].update(time=message_time, balance=balance)]

        await client.close_connection()

    def ticker_run(self):
        self._twm = get_threaded_web_socket_manager()

        self._twm.start_user_socket(callback=self.handle_user_socket_message)

    def ticker_stop(self):
         self._twm.stop()

    def handle_user_socket_message(self, msg):
            print(f"message type: {msg['e']}")
            print(msg)

            message_time = datetime.datetime.fromtimestamp(int(msg['E']) / 1000)

            if msg['e'] == 'outboundAccountPosition':
                for balance in msg['B']:
                    message_time = datetime.datetime.fromtimestamp(int(msg['E']) / 1000)
                    self._assets[balance['a']].update(time=message_time, balance=balance)

            pass

