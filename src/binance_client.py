from binance.client import Client
from src.bot.config.config_private import BINANCE_API_KEY, BINANCE_API_SECRET

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
products = client.get_exchange_info()

symbols = [product['symbol'] for product in client.get_exchange_info()['symbols']]

ticker = client.get_ticker(symbol=symbols[0])

all_tickers = client.get_all_tickers()




pass


trades = client.get_my_trades(symbol=symbols[0])








pass