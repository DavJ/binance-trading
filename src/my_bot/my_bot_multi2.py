import asyncio
from decimal import Decimal
from basic_tools import (get_binance_client, CONFIGURATION, get_trading_currencies,
                         round_down, TRADING_PAIRS, TRADING_CURRENCIES, cancel_obsolete_orders,
                         get_average_buy_price_for_sell_quantity, get_average_sell_price_for_buy_quantity,
                         get_normalized_close_prices, pair_symbol)
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.statistix import Statistix
from model.user_ticker import UserTicker
from model.order import Order
from model.profit import Profit
from time import sleep
from datetime import datetime
from model.kalman2 import Kalman2
import math

class Application:

    def __init__(self):

        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
        self.active_orders = []
        self.profit = Profit()

        #self.symbol_tickers = {}

        self.assets = {currency: Asset(currency=currency) for currency in TRADING_CURRENCIES}

        self.order_books = {curr1 + curr2: OrderBook(currency=curr1, trade_currency=curr2)
                            for curr1, curr2 in TRADING_PAIRS}

        self.statistixes = {curr1 + curr2: Statistix(currency=curr1, trade_currency=curr2)
                            for curr1, curr2 in TRADING_PAIRS}
        self.relative_prices = None

        self.kalman_filter = Kalman2()

    def main(self):
        while True:
            try:
                self.update()
                self.trade()
            except Exception:
                pass

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(int(CONFIGURATION.SLEEP)))

    def update(self):
        for _, asset in self.assets.items():
            asset.get_balance()
            asset.update_last_trades()

        for _, order_book in self.order_books.items():
            order_book.update()

        for _, statistix in self.statistixes.items():
            statistix.update()

        self.relative_prices = get_normalized_close_prices()

    def price_prediction(self, currency):
        """
        returns price prediction for next hours
        :param currency:
        :return:
        """
        return self.symbol_tickers[currency].predict_price

    def price_move_prediction(self, currency):
        """
        returns relative price move prediction for next hours
        :param currency:
        :return:
        """
        return self.symbol_tickers[currency].predict_move

    def max_growth_predicted(self, currency):
        try:
            return max((move for _, move in self.price_move_prediction(currency).items()))
        except AttributeError:
            return 0

    def min_drop_predicted(self, currency):
        try:
            return min((move for _, move in self.price_move_prediction(currency).items()))
        except AttributeError:
            return 0

    def trade(self):

        def update_assets(assets):
            for asset in assets:
                asset.get_balance()
                asset.update_last_trades()

        pre_sorted_order_books = [order_book for _, order_book in self.order_books.items() if order_book.avg_price_relative_difference is not None]

        sorted_order_books = sorted(pre_sorted_order_books, key=lambda x: x.min_price_relative_difference, reverse=True)

        #might change slightly during algorithm due to async refresh of assets, but approximate value is OK
        total_asset_amount_in_main_currency = sum([asset.asset_amount_in_main_currency_market
                                                   for currency, asset in self.assets.items()])

        print(f'\n\nCurrently having approximately {total_asset_amount_in_main_currency} {CONFIGURATION.MAIN_CURRENCY} in total.\n\n')

        self.kalman_filter.update()

        cancel_obsolete_orders()

        #mutual algorithm
        for prediction in self.kalman_filter.sorted_predictions:

            if abs(prediction[1]) < CONFIGURATION.VOLATILITY_COEFICIENT:
                break

            currency = prediction[0][0]
            trade_currency = prediction[0][1]
            pair = pair_symbol(prediction[0])

            order_book = self.order_books[pair]
            statistix = self.statistixes[pair]

            asset = self.assets[currency]
            trade_asset = self.assets[trade_currency]

            buy_limit_price = order_book.strategical_buying_price
            if (trade_asset.asset_amount_free > 0
                and statistix.average_price > buy_limit_price
                and self.max_growth_predicted(currency) >= 0):
                    buy_amount = max(0, trade_asset.asset_amount_free*Decimal(CONFIGURATION.MAX_ASSET_FRACTION) / buy_limit_price)
                    avg_sell_price = get_average_sell_price_for_buy_quantity(buy_amount, currency, trade_currency)

                    if buy_limit_price <= Profit().profitable_buy_price_for_previous_sell_price(avg_sell_price):
                        self.active_orders.append(Order(side='BUY', currency=asset.currency, amount=buy_amount,
                                                  limit_price=buy_limit_price, trade_currency=trade_currency))

                        update_assets([asset, trade_asset])

            sell_limit_price = order_book.strategical_selling_price
            if (asset.asset_amount_free > 0
                and statistix.average_price < sell_limit_price
                and self.min_drop_predicted(asset.currency) <= 0):
                   sell_amount = max(0, asset.asset_amount_free * Decimal(CONFIGURATION.MAX_ASSET_FRACTION))
                   avg_buy_price = get_average_buy_price_for_sell_quantity(sell_amount, currency, trade_currency)

                   if sell_limit_price >= Profit().profitable_sell_price_for_previous_buy_price(avg_buy_price):
                       self.active_orders.append(Order(side='SELL', currency=asset.currency, amount=sell_amount,
                                                 limit_price=sell_limit_price, trade_currency=trade_currency))

                   update_assets([asset, trade_asset])

        print(f'trading iteration finished  at {datetime.now().isoformat()}\n\n')

    def cancel_old_orders(self):
        pass

def full_stack():
    import traceback, sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        del stack[-1]       # remove call of full_stack, the printed exception
                            # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
         stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr

if __name__ == "__main__":
    application = Application()
    try:
        application.main()
    except:
        full_stack()
