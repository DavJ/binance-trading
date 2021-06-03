from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION

class Profit:

    def __init__(self):

        self.buy_profit = Decimal(CONFIGURATION.BUY_PROFIT)
        self.sell_profit = Decimal(CONFIGURATION.SELL_PROFIT)
        self.buy_fee = Decimal(CONFIGURATION.BUY_FEE)
        self.sell_fee = Decimal(CONFIGURATION.SELL_FEE)

        if (self.buy_profit < self.buy_fee) or (self.sell_profit < self.sell_fee):
            raise ('Fees greater than profit')


    def profitable_sell_price_for_previous_buy_price(self, last_buy_price):
        new_price = last_buy_price * (1 + self.sell_profit) / (1 - self.sell_fee)
        assert new_price > last_buy_price
        return new_price

    def profitable_buy_price_for_previous_sell_price(self, last_sell_price):
        new_price = (last_sell_price / (1 + self.buy_profit)) / (1 - self.buy_fee)
        assert new_price < last_sell_price
        return new_price
