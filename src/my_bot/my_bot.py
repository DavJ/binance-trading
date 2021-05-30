from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION, get_trading_currencies, round_down
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.user_ticker import UserTicker
from model.order import Order
from time import sleep
import math

class Application:

    def __init__(self):
        self.user_ticker = UserTicker()
        self.symbol_tickers = {}
        self.order_books = {}
        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = float(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.main_currency_fraction = float(CONFIGURATION.MAIN_CURRENCY_FRACTION)
        self.buy_fee = float(CONFIGURATION.BUY_FEE)
        self.sell_fee = float(CONFIGURATION.SELL_FEE)
        self.minimal_earnings = float(CONFIGURATION.MINIMAL_EARNINGS)
        self.active_orders = []

        for currency in get_trading_currencies():
            self.symbol_tickers.update(**{currency: Ticker(currency)})
            self.order_books.update(**{currency: OrderBook(currency)})

    def main(self):
        while True:
            for _, order_book in self.order_books.items():
                order_book.update()
            self.trade()
            sleep(20)

    def trade(self):
        sorted_order_books = sorted(self.order_books.values(), key=lambda x: x.avg_price_difference, reverse=True)
        #BUY algorithm
        for order_book in sorted_order_books:
            if self.user_ticker.assets[self.main_currency].asset_amount_free <= self.minimal_main_currency_balance:
                break
            buy_amount_main_currency = round_down((self.user_ticker.assets[self.main_currency].asset_amount_free - self.minimal_main_currency_balance) * self.main_currency_fraction, 1)
            asset = self.user_ticker.assets[order_book.currency]
            if (buy_amount_main_currency >=0
                and order_book.avg_buy_price <= asset.recent_average_sell_price - self.minimal_earnings - self.sell_fee):
                buy_amount = round_down(buy_amount_main_currency * order_book.avg_buy_price, 1)
                self.active_orders.append(
                    Order(side='BUY', currency=asset.currency, amount=buy_amount, price=order_book.avg_buy_price))

        #SELL algorithm
        for order_book in self.order_books.values():
            asset = self.user_ticker.assets[order_book.currency]
            max_sell_amount = round_down(asset.asset_amount_free, 1)
            if (max_sell_amount >=0
                and order_book.avg_sell_price >= asset.recent_average_buy_price + self.minimal_earnings + self.sell_fee):
                   self.active_orders.append(Order(side='SELL', currency=asset.currency, amount=max_sell_amount, price=order_book.avg_sell_price))

if __name__ == "__main__":
    application = Application()
    application.main()
