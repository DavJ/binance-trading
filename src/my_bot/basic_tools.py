from decimal import Decimal
import os
import sys
import asyncio
import math
import decouple
from binance.client import Client, AsyncClient
from binance import ThreadedWebsocketManager, BinanceSocketManager
from functools import reduce

INI_FILE = os.path.dirname(os.path.realpath(__file__)) + '/settings.ini'

config = decouple.Config(decouple.RepositoryEnv(INI_FILE))


def get_binance_client():
    return Client(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))


async def get_async_binance_client():
    async_client = await AsyncClient.create(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))
    return async_client


def get_threaded_web_socket_manager():
    twm = ThreadedWebsocketManager(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))
    twm.start()  # needed to start internal loop
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


def get_trading_currencies():
    return (config('TRADING_CURRENCIES').replace(' ', '').split(','))


def get_evaluation_currencies():
    return get_trading_currencies() + [config('MAIN_CURRENCY')]


def use_async_client():
    return bool(CONFIGURATION.USE_ASYNC_CLIENT.lower() == 'true')


def fix_none(arg):
    if arg is None:
        return Decimal('0')
    else:
        return arg

def round_down(x, decimal_places):
    return math.floor(x * 10 ** decimal_places) / 10 ** decimal_places

def round_up(x, decimal_places):
    return math.ceil(x * 10 ** decimal_places) / 10 ** decimal_places

def format_to_precision(x, precision):
    return Decimal(str(x)).quantize(Decimal(str(10**-precision)))

    #return f'{x:.{precision}}'

def ilen(iterable):
    return reduce(lambda sum, element: sum + 1, iterable, 0)


def get_order_book_statistics(pair):
    client = get_binance_client()
    ticker = client.get_order_book(symbol=pair)
    _bids = ticker['bids']
    _asks = ticker['asks']

    total_bid = sum([float(bid[1]) for bid in _bids])
    total_ask = sum([float(ask[1]) for ask in _asks])
    avg_buy_price = sum([float(bid[0]) * float(bid[1]) for bid in _bids]) / total_bid
    avg_sell_price = sum([float(ask[0]) * float(ask[1]) for ask in _asks]) / total_ask
    avg_price_difference = avg_sell_price - avg_buy_price
    max_sell_price = max([float(ask[0]) for ask in _asks])
    min_buy_price = min([float(bid[0]) for bid in _bids])
    max_price_difference = max_sell_price - min_buy_price

    return dict(
        _bids = _bids,
        _asks = _asks,
        total_bid=total_bid,
        avg_buy_price=avg_buy_price,
        min_sell_price=min([float(ask[0]) for ask in _asks]),
        max_sell_price=max_sell_price,
        max_buy_price=max([float(bid[0]) for bid in _bids]),
        min_buy_price=min_buy_price,
        total_ask=total_ask,
        avg_sell_price=avg_sell_price,
        avg_price_difference=avg_price_difference,
        avg_price_relative_difference=2 * avg_price_difference / (avg_sell_price + avg_buy_price),
        max_price_difference=max_price_difference,
        max_price_relative_difference=2 * max_price_difference / (max_sell_price + min_buy_price)
    )


class Configuration:

    def __init__(self):
        for attribute in ['MODE', 'TRADING_MODE', 'MAIN_CURRENCY', 'TRADING_CURRENCIES', 'MINIMAL_EARNINGS',
                          'MINIMAL_MAIN_CURRENCY_BALANCE', 'MAIN_CURRENCY_FRACTION',
                          'BUY_FEE', 'SELL_FEE',
                          'DB_FILE', 'VOLATILITY_LIMIT_FACTOR', 'USE_ASYNC_CLIENT', 'SLEEP']:
            setattr(self, attribute, config(attribute))


CONFIGURATION = Configuration()
