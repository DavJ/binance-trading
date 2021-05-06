from binance.client import Client
from config.config_private import API_KEY, API_SECRET

client = Client(API_KEY, API_SECRET)
products = client.get_exchange_info()

symbols = [product['symbol'] for product in client.get_exchange_info()['symbols']]

ticker = client.get_ticker(symbol=symbols[0])

all_tickers = client.get_all_tickers()
pass