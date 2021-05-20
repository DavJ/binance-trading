from src.my_bot.basic_tools import get_binance_client
client = get_binance_client()

products = client.get_exchange_info()
symbols = [product['symbol'] for product in client.get_exchange_info()['symbols']]

ticker = client.get_ticker(symbol=symbols[0])

all_tickers = client.get_all_tickers()

trades = client.get_my_trades(symbol=symbols[0])

pass
