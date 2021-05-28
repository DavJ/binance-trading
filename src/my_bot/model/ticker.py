from datetime import datetime
from decimal import Decimal
import asyncio

import datetime
import aiosqlite
import json

from src.my_bot.basic_tools import (CONFIGURATION, get_binance_client, get_async_binance_client,
                                    use_async_client, get_async_web_socket_manager, get_threaded_web_socket_manager)
from src.my_bot.model.kalman import Kalman

class Ticker:

    def __init__(self, currency=None, asset_currency='BNB'):
        self.currency = currency
        self.asset_currency = asset_currency
        self.pair = currency + asset_currency
        self.time = None
        self.last_price = None
        self._twm = None
        self._async_client = None
        self._filter = None
        if use_async_client():
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.aio_ticker_run())
        else:
            self.ticker_run()

    def __repr__(self):
       return f"Ticker(currency='{self.currency}, asset_currency={self.asset_currency})"

    async def aio_ticker_run(self):
        self._async_client = await get_async_web_socket_manager()
        bm = get_async_web_socket_manager(self._async_client)
        # then start receiving messages
        ts = bm.trade_socket(self.pair)
        async with ts as tscm:
            while True:
                res = await tscm.recv()
                print(res)

        await client.close_connection()

    def ticker_run(self):
        self._twm = get_threaded_web_socket_manager()

        self._twm.start_kline_socket(callback=self.handle_kline_socket_message, symbol=self.pair)

    def ticker_stop(self):
        self._twm.stop

    def handle_kline_socket_message(self, msg):
        #print(f"message type: {msg['e']}")
        #print(msg)

        message_time = datetime.datetime.fromtimestamp(int(msg['E']) / 1000)

        if msg['e'] == 'kline' and msg['k']['s'] == self.pair:
            self.time = message_time
            self.last_price = float(msg['k']['c'])
            self.update_filter()
            print(f'{self.time.isoformat()}: {self.last_price}')

    def update_filter(self):
        if self._filter is None:
            self._filter = Kalman(time=self.time, value=self.last_price)
        else:
            self._filter.update(time=self.time, value=self.last_price)
