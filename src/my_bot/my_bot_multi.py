import asyncio
from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION, get_trading_currencies, round_down, TRADING_PAIRS
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.statistix import Statistix
from model.user_ticker import UserTicker
from model.order import Order
from model.profit import Profit
from time import sleep
from datetime import datetime
import math

class Application:

    def __init__(self):

        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
        self.active_orders = []
        self.profit = Profit()

        self.symbol_tickers = {}
        self.order_books = {curr1 + curr2: OrderBook(currency=curr1, trade_currency=curr2)
                            for curr1, curr2 in TRADING_PAIRS}

        self.statistixes = {curr1 + curr2: Statistix(currency=curr1, trade_currency=curr2)
                            for curr1, curr2 in TRADING_PAIRS}

    def main(self):
        while True:
            for _, order_book in self.order_books.items():
                order_book.update()
            self.trade()
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

    def min_drop_predicted(self, currency):
        try:
            return min((move for _, move in self.price_move_prediction(currency).items()))
        except AttributeError:
            return 0

    def trade(self):
        sorted_order_books = sorted(self.order_books.values(), key=lambda x: x.avg_price_relative_difference, reverse=False)

        #might change slightly during algorithm due to async refresh of assets, but approximate value is OK
        total_asset_amount_in_main_currency = sum([self.user_ticker.assets[key].asset_amount_in_main_currency_market
                                                   for key in self.user_ticker.assets])

        print(f'\n\nCurrently having approximately {total_asset_amount_in_main_currency} {CONFIGURATION.MAIN_CURRENCY} in total.\n\n')

        #mutual algorithm
        for order_book in sorted_order_books:

            currency = order_book.currency
            trade_currency = order_book.trade_currency

            statistix = self.statistixes[currency + trade_currency]

            statistix.update()
            order_book.update()

            asset = self.user_ticker.assets[order_book.currency]
            trade_asset = self.user_ticker.assets[order_book.trade_currency]

            buy_limit_price = order_book.strategical_buying_price
            if (asset.asset_amount_free > 0
                and statistix.average_price > buy_limit_price
                and self.max_growth_predicted(asset.currency) >= 0):
                    buy_amount = max(0, asset.asset_amount_free*Decimal(CONFIGURATION.MAX_ASSET_FRACTION))
                    if not CONFIGURATION.PLACE_BUY_ORDER_ONLY_IF_PRICE_MATCHES:
                        self.active_orders.append(
                            Order(side='BUY', currency=asset.currency, amount=buy_amount, limit_price=buy_limit_price,
                                  trade_currency=trade_currency))


            sell_limit_price = order_book.strategical_selling_price
            if (trade_asset.asset_amount_free > 0
                and statistix.average_price < sell_limit_price
                and self.min_drop_predicted(trade_asset.currency) <= 0):
                   sell_amount = max(0, trade_asset.asset_amount_free * Decimal(CONFIGURATION.MAX_ASSET_FRACTION))
                   self.active_orders.append(Order(side='SELL', currency=asset.currency, amount=sell_amount,
                                                   limit_price=sell_limit_price, trade_currency=trade_currency))

        print(f'trading iteration finished  at {datetime.now().isoformat()}\n\n')

if __name__ == "__main__":
    application = Application()
    application.main()
