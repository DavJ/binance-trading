from decimal import Decimal
from basic_tools import get_binance_client, CONFIGURATION
from model.asset import Asset


client = get_binance_client()

#act=client.get_account()
#trading_mode = CONFIGURATION.trading_mode
#pass

asset = Asset('BNB')
#asset = Asset('BTC')

pass