AVAILABLE_EXCHANGES="coinbase,binance"
EXCHANGE="binance"

BINANCE_API_KEY="<PlaceHolder>"
BINANCE_API_SECRET="<PlaceHolder>"

COINBASE_API_KEY="<PlaceHolder>"
COINBASE_API_SECRET="<PlaceHolder>"

# Available modes
# "trade" to trade on candlesticks
# "live" to live trade throught WebSocket
# "backtest" to test a strategy for a given symbol pair and a period
# "import" to import dataset from exchanges for a given symbol pair and a period
MODE="trade"
STRATEGY="logger"
# Allow trading "test" mode or "real" trading
TRADING_MODE="test"
# Default candle size in seconds
CANDLE_INTERVAL=60
CURRENCY="XRP"
ASSET="EUR"
# Default period for backtesting: string in UTC format
PERIOD_START="2021-02-28T08:49"
PERIOD_END="2021-03-09T08:49"

DATABASE_URL="postgresql://postgres:password@127.0.0.1:15432/cryptobot"


from config_private import *

pass