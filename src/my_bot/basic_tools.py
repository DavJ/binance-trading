from decimal import Decimal
import os
import sys
import asyncio
import decouple
from binance.client import Client, AsyncClient
from binance import ThreadedWebsocketManager, BinanceSocketManager

INI_FILE = os.path.dirname(os.path.realpath(__file__)) + '/settings.ini'

config = decouple.Config(decouple.RepositoryEnv(INI_FILE))

def get_binance_client():
    return Client(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))

async def get_async_binance_client():
    async_client = await AsyncClient.create(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))
    return async_client

def get_threaded_web_socket_manager():
    twm = ThreadedWebsocketManager(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))
    twm.start() #needed to start internal loop
    return twm

async def get_async_web_socket_manager():
    awm = await get_async_binance_client()
    bm = BinanceSocketManager(awm)
    return bm


def get_java_name(text, title_first=True):
    # saving first and rest using split()
    init, *temp = text.split('_')
    if title_first:
        return ''.join([init.title(), *map(str.title, temp)])
    else:
        return ''.join([init.lower(), *map(str.title, temp)])

def get_currency_pair(currency1, currency2):
    sorted_pair = sorted([currency1, currency2])  # assume pairs are created alphabetically
    return sorted_pair[0] + sorted_pair[1]

def use_async_client():
    return bool(CONFIGURATION.USE_ASYNC_CLIENT.lower() == 'true')

def fix_none(arg):
    if arg is None:
        return Decimal('0')
    else:
        return arg

class Configuration:

    def __init__(self):
        for attribute in ['MODE', 'TRADING_MODE', 'CURRENCY', 'ASSET', 'TRADING_CURRENCIES', 'MINIMAL_EARNINGS',
                          'DB_FILE', 'VOLATILITY_LIMIT_FACTOR', 'USE_ASYNC_CLIENT']:
            setattr(self, attribute, config(attribute))


CONFIGURATION = Configuration()
