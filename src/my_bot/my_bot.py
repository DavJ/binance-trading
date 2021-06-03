from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION, get_trading_currencies, round_down
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.user_ticker import UserTicker
from model.order import Order
from model.profit import Profit
from time import sleep
import math

class Application:

    def __init__(self):
        self.user_ticker = UserTicker()
        self.symbol_tickers = {}
        self.order_books = {}
        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.main_currency_fraction = Decimal(CONFIGURATION.MAIN_CURRENCY_FRACTION)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
        self.minimal_earnings = Decimal(CONFIGURATION.MINIMAL_EARNINGS)
        self.active_orders = []
        self.profit = Profit()

        for currency in get_trading_currencies():
            self.symbol_tickers.update(**{currency: Ticker(currency)})
            self.order_books.update(**{currency: OrderBook(currency)})

    def main(self):
        while True:
            for _, order_book in self.order_books.items():
                order_book.update()
            self.trade()
            sleep(int(CONFIGURATION.SLEEP))

    def trade(self):
        sorted_order_books = sorted(self.order_books.values(), key=lambda x: x.avg_price_difference, reverse=True)
        #BUY algorithm
        for order_book in sorted_order_books:
            if self.user_ticker.assets[self.main_currency].asset_amount_free <= self.minimal_main_currency_balance:
                break
            buy_amount_main_currency = (self.user_ticker.assets[self.main_currency].asset_amount_free - self.minimal_main_currency_balance) * self.main_currency_fraction
            asset = self.user_ticker.assets[order_book.currency]
            if (buy_amount_main_currency >= 0):
                buy_amount = buy_amount_main_currency / order_book.avg_buy_price
                self.active_orders.append(
                    Order(side='BUY', currency=asset.currency, amount=buy_amount))

        #SELL algorithm
        for order_book in self.order_books.values():
            asset = self.user_ticker.assets[order_book.currency]
            max_sell_amount = asset.asset_amount_free
            if (max_sell_amount > 0):
                   self.active_orders.append(Order(side='SELL', currency=asset.currency, amount=max_sell_amount))

if __name__ == "__main__":
    application = Application()
    application.main()
