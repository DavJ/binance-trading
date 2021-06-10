import asyncio
from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION, get_trading_currencies, round_down
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from model.user_ticker import UserTicker
from model.order import Order
from model.profit import Profit
from time import sleep
from datetime import datetime
import math

class Application:

    def __init__(self):
        self.user_ticker = UserTicker()
        self.symbol_tickers = {}
        self.order_books = {}
        self.main_currency = CONFIGURATION.MAIN_CURRENCY
        self.minimal_main_currency_balance = Decimal(CONFIGURATION.MINIMAL_MAIN_CURRENCY_BALANCE)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)
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
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(int(CONFIGURATION.SLEEP)))
            #sleep(int(CONFIGURATION.SLEEP))

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

            if (allowed_buy_amount_in_main_currency > 0) and asset.statistix.price_eligible_for_buy(limit_price):
                buy_amount = allowed_buy_amount_in_main_currency / order_book.avg_buy_price
                self.active_orders.append(
                    Order(side='BUY', currency=asset.currency, amount=buy_amount, limit_price=limit_price))

        #SELL algorithm
        for order_book in self.order_books.values():
            asset = self.user_ticker.assets[order_book.currency]
            max_sell_amount = asset.asset_amount_free
            limit_price = order_book.strategical_selling_price
            if (max_sell_amount > 0) and asset.statistix.price_eligible_for_sell(limit_price):
                   self.active_orders.append(Order(side='SELL', currency=asset.currency, amount=max_sell_amount, limit_price=limit_price))

        print(f'trading iteration finished  at {datetime.now().isoformat()}\n\n')

if __name__ == "__main__":
    application = Application()
    application.main()
