import decouple
from binance.client import Client

config = decouple.Config(decouple.RepositoryEnv('settings.ini'))

def get_binance_client():

    return Client(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))

def get_java_name(text, title_first=True):
    # saving first and rest using split()
    init, *temp = text.split('_')
    if title_first:
        return ''.join([init.title(), *map(str.title, temp)])
    else:
        return ''.join([init.lower(), *map(str.title, temp)])

class Configuration:

    def __init__(self):
        for attribute in ['MODE', 'TRADING_MODE', 'CURRENCY', 'ASSET']:
            setattr(self, attribute.lower(), config(attribute))

CONFIGURATION = Configuration()
