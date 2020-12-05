from binance.client import Client
from config_private import BINANCE_API_KEY, BINANCE_API_SECRET

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
products = client.get_exchange_info()

pass