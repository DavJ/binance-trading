from decimal import Decimal
import os
import sys
import asyncio
import math
import decouple
from binance.client import Client, AsyncClient
from binance import ThreadedWebsocketManager, BinanceSocketManager
from functools import reduce
from datetime import datetime, timedelta
import numpy as np
from binance.enums import HistoricalKlinesType
from binance.exceptions import BinanceAPIException

INI_FILE = os.path.dirname(os.path.realpath(__file__)) + '/settings.ini'

config = decouple.Config(decouple.RepositoryEnv(INI_FILE))

class Configuration:

    def __init__(self):
        for attribute in ['MAIN_CURRENCY', 'TRADING_CURRENCIES', 'MINIMAL_MAIN_CURRENCY_BALANCE',
                          'BUY_FEE', 'SELL_FEE', 'BUY_PROFIT', 'SELL_PROFIT', 'BUY_STRATEGY', 'SELL_STRATEGY',
                          'DB_FILE', 'USE_ASYNC_CLIENT', 'MAX_ASSET_FRACTION', 'SLEEP',
                          'BUY_DAILY_CHANGER', 'SELL_DAILY_CHANGER', 'SELL_IMMEDIATELY',
                          'PLACE_BUY_ORDER_ONLY_IF_PRICE_MATCHES', 'ORDER_VALIDITY', 'VOLATILITY_COEFICIENT']:
            setattr(self, attribute, config(attribute))


CONFIGURATION = Configuration()

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

def get_main_currency_pairs():
    pairs = []
    main_currency = config('MAIN_CURRENCY')
    trading_currencies = get_trading_currencies()
    trading_symbols = {s['symbol'] for s in get_exchange_info()['symbols']}
    for currency1 in trading_currencies:
        for currency2 in trading_currencies:
            if currency1 + currency2 in trading_symbols:
                if currency1 == main_currency or currency2 == main_currency:
                    pairs.append((currency1, currency2,))
    return sorted(pairs)

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

    if total_bid > 0:
        avg_buy_price = sum([Decimal(bid[0]) * Decimal(bid[1]) for bid in _bids]) / total_bid
    else:
        avg_buy_price = None

    if total_ask > 0:
        avg_sell_price = sum([Decimal(ask[0]) * Decimal(ask[1]) for ask in _asks]) / total_ask
    else:
        avg_sell_price = None

    try:
        avg_market_price = (avg_buy_price * total_bid + avg_sell_price * total_ask) / (total_bid + total_ask)
    except TypeError:
        avg_market_price = None
    except ZeroDivisionError:
         avg_market_price = None

    try:
        avg_price_difference = avg_sell_price - avg_buy_price
    except TypeError:
        avg_price_difference = None

    try:
        min_sell_price = min([Decimal(ask[0]) for ask in _asks])
    except ValueError:
        min_sell_price = None

    try:
        max_sell_price = max([Decimal(ask[0]) for ask in _asks])
    except ValueError:
        max_sell_price = None

    try:
        min_buy_price = min([Decimal(bid[0]) for bid in _bids])
    except ValueError:
        min_buy_price = None

    try:
        max_buy_price = max([Decimal(bid[0]) for bid in _bids])
    except ValueError:
        max_buy_price = None

    try:
        max_price_difference = max_sell_price - min_buy_price
    except TypeError:
        max_price_difference = None

    try:
        min_price_difference = min_sell_price - max_buy_price
    except TypeError:
        min_price_difference = None

    try:
        avg_price_relative_difference = 2 * avg_price_difference / (avg_sell_price + avg_buy_price)
    except TypeError:
        avg_price_relative_difference = None

    try:
        max_price_relative_difference = 2 * max_price_difference / (max_sell_price + min_buy_price)
    except TypeError:
        max_price_relative_difference = None

    try:
        min_price_relative_difference = 2 * min_price_difference / (min_sell_price + max_buy_price)
    except TypeError:
        min_price_relative_difference = None


    return dict(
        _bids=_bids,
        _asks=_asks,
        total_bid=total_bid,
        avg_buy_price=avg_buy_price,
        min_sell_price=min_sell_price,
        max_sell_price=max_sell_price,
        max_buy_price=max_buy_price,
        min_buy_price=min_buy_price,
        total_ask=total_ask,
        avg_sell_price=avg_sell_price,
        avg_price_difference=avg_price_difference,
        avg_price_relative_difference=avg_price_relative_difference,
        max_price_difference=max_price_difference,
        max_price_relative_difference=max_price_relative_difference,
        min_price_difference=min_price_difference,
        min_price_relative_difference=min_price_relative_difference,
        avg_current_price=avg_current_price,
        avg_market_price=avg_market_price
    )


def get_average_buy_price_for_sell_quantity(trade_quantity, currency, trade_currency=CONFIGURATION.MAIN_CURRENCY):
    return get_recent_opposite_trade_price_for_trade_quantity(trade_quantity=trade_quantity,
                                                currency=currency,
                                                trade_currency=trade_currency,
                                                side='SELL')

def get_average_sell_price_for_buy_quantity(trade_quantity, currency, trade_currency=CONFIGURATION.MAIN_CURRENCY):
    return get_recent_opposite_trade_price_for_trade_quantity(trade_quantity=trade_quantity,
                                                currency=currency,
                                                trade_currency=trade_currency,
                                                side='BUY')

def get_recent_opposite_trade_price_for_trade_quantity(trade_quantity, currency, trade_currency=CONFIGURATION.MAIN_CURRENCY, side='BUY'):

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

    if currency != trade_currency:
        client = get_binance_client()
        asset_trades = client.get_my_trades(symbol=currency + trade_currency, limit=100)

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
            statistics = get_order_book_statistics(currency + trade_currency)
            return statistics['avg_buy_price'] if side == 'SELL' else statistics['avg_sell_price']

TRADING_CURRENCIES = get_trading_currencies()
TRADING_PAIRS = get_trading_pairs()
PAIR_SYMBOLS = [pair[0] + pair[1] for pair in TRADING_PAIRS]
DIRECTIONAL_PAIRS = [pair for pair in TRADING_PAIRS] + [(pair[1], pair[0]) for pair in TRADING_PAIRS]


def possible_paths(currency, max_depth=3):
    paths = []
    if max_depth > 0:
        matching_pairs = [pair for pair in DIRECTIONAL_PAIRS if pair[0] == currency]
        for pair in matching_pairs:
            paths.append(pair)
            for next_path in possible_paths(pair[1], max_depth=max_depth - 1):
                paths.append(pair + next_path)

    return paths

def possible_rounds(max_depth=3):
    rounds = []
    for c in TRADING_CURRENCIES:
        for p in possible_paths(c, max_depth=max_depth):
            if p[-1] == c:
                rounds.append(p)
    return rounds

def get_all_obsolete_orders():
    client = get_binance_client()
    orders = client.get_open_orders()
    return [(order['symbol'], order['orderId']) for order in orders
            if datetime.fromtimestamp(order['time']/1000) < datetime.now() - timedelta(minutes=int(CONFIGURATION.ORDER_VALIDITY))]

def cancel_obsolete_orders():
    client = get_binance_client()
    for obsolete_order in get_all_obsolete_orders():
        client.cancel_order(symbol=obsolete_order[0], orderId=obsolete_order[1])
        print(f'Cancelling order {obsolete_order}')

def get_historical_klines(pair, limit=500):
    client = get_binance_client()
    start_timestamp = int((datetime.now() - timedelta(minutes=15*limit)).timestamp()*1000)
    return client.get_historical_klines(symbol=pair, interval=Client.KLINE_INTERVAL_15MINUTE,
                                        start_str=start_timestamp, #limit=limit,
                                        klines_type=HistoricalKlinesType.SPOT)

def normalize_rate(past_rate, current_rate, scale=1):
    return 2*math.atan(scale*(Decimal(past_rate)/Decimal(current_rate) - 1))/math.pi

def get_close_price(pair):
    """
    refer to https://github.com/binance-us/binance-official-api-docs/blob/master/rest-api.md#klinecandlestick-data
    close_price has index 4
    """
    scale = 10
    olhvc_history = get_historical_klines(pair[0] + pair[1])
    return [olhvc_history[-1][4] for sample in olhvc_history]

def get_normalized_close_price(pair):
    """
    refer to https://github.com/binance-us/binance-official-api-docs/blob/master/rest-api.md#klinecandlestick-data
    close_price has index 4
    """
    scale = 10
    olhvc_history = get_historical_klines(pair[0] + pair[1])
    return [normalize_past_rate(sample[4], olhvc_history[-1][4], scale) for sample in olhvc_history]

def get_normalized_close_price_train_data_for_pair(pair):
    M, N = 5, 5   #N ... split to chunks of length 2^N, M .... predict exponent
    cp = get_normalized_close_price(pair)
    train_data = [[cp[i + k**2 - j**2] for k in range(M) for j in range(N)] for i in range(2**N, len(cp) - 2**M)] #TODO looks wrong
    #train_data = [[cp[i + k ** 2 - j ** 2] for k in range(M) for j in range(N)] for i inrange(2 ** N, len(cp) - 2 ** M)]

    return np.array(train_data)

def get_normalized_close_price_train_data_by_pairs():
    return {pair: get_normalized_close_price_train_data_for_pair(pair[0] + pair[1]) for pair in get_main_currency_pairs()}

def get_normalized_close_prices():
    return {pair: get_normalized_close_price(pair[0] + pair[1]) for pair in get_main_currency_pairs()}
