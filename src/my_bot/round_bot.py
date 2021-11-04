import asyncio
from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION, get_trading_currencies, round_down, get_trading_pairs
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.user_ticker import UserTicker
from model.order import Order
from model.profit import Profit
from time import sleep
from datetime import datetime
import math
from binance.exceptions import BinanceAPIException

from src.my_bot.model.statistix import Statistix

TRADING_CURRENCIES = get_trading_currencies()
TRADING_PAIRS = get_trading_pairs()
DIRECTIONAL_PAIRS = [pair for pair in TRADING_PAIRS] + [(pair[1], pair[0]) for pair in TRADING_PAIRS]

class Application:

    def __init__(self):
        #self.user_ticker = UserTicker()
        #self.symbol_tickers = {}
        #self.order_books = {}
        #self.main_currency = CONFIGURATION.MAIN_CURRENCY
        #self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        #self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        #self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
        #self.active_orders = []
        #self.profit = Profit()


        #self.symbol_tickers.update(**{currency: Ticker(currency)})
        #self.order_books.update(**{currency: OrderBook(currency)})
        pass

        #def statistix_pair_generator():
        #    for currency1 in get_trading_currencies():
        #        for currency2 in get_trading_currencies():
        #            if currency1 != currency2:
        #                try:
        #                   yield currency1, currency2, Statistix(currency=currency1, main_currency=currency2)
        #                except BinanceAPIException as exc:
        #                  pass

        self.statistix_pairs = [Statistix(currency=curr1, main_currency=curr2) for curr1, curr2 in get_trading_pairs()]

        def possible_paths(currency, max_depth=3):
            paths = []
            if max_depth > 0:
                matching_pairs = [pair for pair in DIRECTIONAL_PAIRS if pair[0] == currency]
                for pair in matching_pairs:
                    paths.append(pair)
                    for next_path in possible_paths(pair[1], max_depth=max_depth-1):
                        paths.append(pair + next_path)

            return paths

        def possible_rounds():
            rounds = []
            for c in TRADING_CURRENCIES:
                for p in possible_paths(c):
                    if p[-1] == c:
                        rounds.append(p)
            return rounds

        self.possible_rounds = possible_rounds()
        pass


    def main(self):
        while True:
            for _, order_book in self.order_books.items():
                order_book.update()
            #self.trade()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(int(CONFIGURATION.SLEEP)))
            #sleep(int(CONFIGURATION.SLEEP))

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
        return self.symbol_tickers[currency].predict_price_move

    def max_growth_predicted(self, currency):
        try:
            return max((move for _, move in self.price_move_prediction(currency).items()))
        except AttributeError:
            return 0

    def trade(self):
        sorted_order_books = sorted(self.order_books.values(), key=lambda x: x.avg_price_difference, reverse=True)

        #might change slightly during algorithm due to async refresh of assets, but approximate value is OK
        total_asset_amount_in_main_currency = sum([self.user_ticker.assets[key].asset_amount_in_main_currency_market
                                                   for key in self.user_ticker.assets])

        print(f'\n\nCurrently having approximately {total_asset_amount_in_main_currency} {CONFIGURATION.MAIN_CURRENCY} in total.\n\n')

        #BUY algorithm
        for order_book in sorted_order_books:
            if self.user_ticker.assets[self.main_currency].asset_amount_free <= self.minimal_main_currency_balance:
                break
            buy_amount_in_main_currency = (self.user_ticker.assets[self.main_currency].asset_amount_free - self.minimal_main_currency_balance)
            max_asset_amount_allowed_in_main_currency = total_asset_amount_in_main_currency * Decimal(CONFIGURATION.MAX_ASSET_FRACTION)
            allowed_buy_amount_in_main_currency = max(0, buy_amount_in_main_currency - max_asset_amount_allowed_in_main_currency)

            asset = self.user_ticker.assets[order_book.currency]
            limit_price = order_book.strategical_buying_price

            if ((allowed_buy_amount_in_main_currency > 0) #and asset.statistix.eligible_for_buy()
                 and self.max_growth_predicted(asset.currency) >= 0):
                buy_amount = max(0, allowed_buy_amount_in_main_currency / order_book.avg_buy_price - asset.asset_amount_total)
                if not CONFIGURATION.PLACE_BUY_ORDER_ONLY_IF_PRICE_MATCHES or order_book.min_buy_price <= limit_price:
                    self.active_orders.append(
                        Order(side='BUY', currency=asset.currency, amount=buy_amount, limit_price=limit_price))

        #SELL algorithm
        for order_book in self.order_books.values():
            asset = self.user_ticker.assets[order_book.currency]
            max_sell_amount = asset.asset_amount_free
            limit_price = order_book.strategical_selling_price
            if (max_sell_amount > 0) and asset.statistix.eligible_for_sell():
                   self.active_orders.append(Order(side='SELL', currency=asset.currency, amount=max_sell_amount, limit_price=limit_price))

        print(f'trading iteration finished  at {datetime.now().isoformat()}\n\n')

if __name__ == "__main__":
    application = Application()
    application.main()
