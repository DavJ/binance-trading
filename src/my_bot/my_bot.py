from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION
from model.asset import Asset
from model.ticker import Ticker
from model.order_book import OrderBook
from time import sleep

client = get_binance_client()

#act=client.get_account()
#trading_mode = CONFIGURATION.trading_mode
#pass

main_asset = Asset('BNB')
asset_ada = Asset('ADA')
pass
ticker = Ticker('ADA')
order_book = OrderBook('ADA')

while True:
    depth = get_binance_client().get_order_book(symbol='ADABNB')
    tickers = client.get_orderbook_tickers()
    best_prices = client.get_orderbook_ticker()
    order_book.update()
    ticker.update_chart()
    sleep(5)
