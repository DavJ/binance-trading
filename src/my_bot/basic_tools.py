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

def get_exchange_info():
    return get_binance_client().get_exchange_info()

def get_trading_pairs():
    pairs = []
    trading_currencies = get_trading_currencies()
    trading_symbols = {s['symbol'] for s in get_exchange_info()['symbols']}
    for currency1 in trading_currencies:
        for currency2 in trading_currencies:
            if currency1 + currency2 in trading_symbols:
                pairs.append((currency1, currency2,))
    return pairs

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

    avg_current_price = Decimal(client.get_avg_price(symbol=pair)['price'])

    total_bid = sum([Decimal(bid[1]) for bid in _bids])
    total_ask = sum([Decimal(ask[1]) for ask in _asks])
    avg_buy_price = sum([Decimal(bid[0]) * Decimal(bid[1]) for bid in _bids]) / total_bid
    avg_sell_price = sum([Decimal(ask[0]) * Decimal(ask[1]) for ask in _asks]) / total_ask
    avg_price_difference = avg_sell_price - avg_buy_price
    max_sell_price = max([Decimal(ask[0]) for ask in _asks])
    min_buy_price = min([Decimal(bid[0]) for bid in _bids])
    max_price_difference = max_sell_price - min_buy_price



    return dict(
        _bids = _bids,
        _asks = _asks,
        total_bid=total_bid,
        avg_buy_price=avg_buy_price,
        min_sell_price=min([Decimal(ask[0]) for ask in _asks]),
        max_sell_price=max_sell_price,
        max_buy_price=max([Decimal(bid[0]) for bid in _bids]),
        min_buy_price=min_buy_price,
        total_ask=total_ask,
        avg_sell_price=avg_sell_price,
        avg_price_difference=avg_price_difference,
        avg_price_relative_difference=2 * avg_price_difference / (avg_sell_price + avg_buy_price),
        max_price_difference=max_price_difference,
        max_price_relative_difference=2 * max_price_difference / (max_sell_price + min_buy_price),
        avg_current_price=avg_current_price
    )


def get_average_buy_price_for_sell_quantity(trade_quantity, currency, main_currency='BNB'):
    return get_recent_opposite_trade_price_for_trade_quantity(trade_quantity=trade_quantity,
                                                currency=currency,
                                                main_currency=main_currency,
                                                side='SELL')

def get_average_sell_price_for_buy_quantity(trade_quantity, currency, main_currency='BNB'):
    return get_recent_opposite_trade_price_for_trade_quantity(trade_quantity=trade_quantity,
                                                currency=currency,
                                                main_currency=main_currency,
                                                side='BUY')

def get_recent_opposite_trade_price_for_trade_quantity(trade_quantity, currency, main_currency='BNB', side='BUY'):

    def calc_average_price_for_asset_amount(quantity, opposite_trades):
        sorted_trades = sorted(opposite_trades, key=lambda x: x['time'], reverse=True)
        sum, weighted_sum, remaining_quantity = Decimal(0), Decimal(0), Decimal(trade_quantity)
        for opposite_trade in sorted_trades:
            opposite_trade_quantity = Decimal(opposite_trade['qty'])
            opposite_trade_price = Decimal(opposite_trade['price'])
            used_quantity = min(opposite_trade_quantity, remaining_quantity)
            sum += used_quantity
            weighted_sum += opposite_trade_price * used_quantity
            remaining_quantity = max(0, remaining_quantity-used_quantity)
            if remaining_quantity == 0:
                break
        if sum != 0:
            return weighted_sum / sum
        else:
            raise(f'Division by zero missing previous trades or zero trade quantity. Trade quantity={trade_quantity}')

    if currency != main_currency:
        client = get_binance_client()
        asset_trades = client.get_my_trades(symbol=currency + main_currency, limit=100)

        if side == 'BUY':
            opposite_side_trades = list(filter(lambda x: not x['isBuyer'], asset_trades))
        elif side == 'SELL':
            opposite_side_trades = list(filter(lambda x: x['isBuyer'], asset_trades))
        else:
            raise(f'unknown side {side}')

        try:
            return  calc_average_price_for_asset_amount(trade_quantity, opposite_trades= opposite_side_trades)
        except Exception:
            # set some initial values
            statistics = get_order_book_statistics(currency + main_currency)
            return statistics['avg_buy_price'] if side == 'SELL' else statistics['avg_sell_price']

class Configuration:

    def __init__(self):
        for attribute in ['MAIN_CURRENCY', 'TRADING_CURRENCIES', 'MINIMAL_MAIN_CURRENCY_BALANCE',
                          'BUY_FEE', 'SELL_FEE', 'BUY_PROFIT', 'SELL_PROFIT', 'BUY_STRATEGY', 'SELL_STRATEGY',
                          'DB_FILE', 'USE_ASYNC_CLIENT', 'MAX_ASSET_FRACTION', 'SLEEP',
                          'BUY_DAILY_CHANGER', 'SELL_DAILY_CHANGER', 'SELL_IMMEDIATELY',
                          'PLACE_BUY_ORDER_ONLY_IF_PRICE_MATCHES']:
            setattr(self, attribute, config(attribute))


CONFIGURATION = Configuration()
