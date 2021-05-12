from decouple import Config, RepositoryEnv
from binance.client import Client

def get_binance_client():
    config = Config(RepositoryEnv('../bot/settings.ini'))
    return Client(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))

def get_java_name(text, title_first=True):
    # saving first and rest using split()
    init, *temp = text.split('_')
    if title_first:
        return ''.join([init.title(), *map(str.title, temp)])
    else:
        return ''.join([init.lower(), *map(str.title, temp)])


from decouple import Config, RepositoryEnv
config = Config(RepositoryEnv('../bot/settings.ini'))
client = Client(config('BINANCE_API_KEY'), config('BINANCE_API_SECRET'))


#print(get_java_name(text='test_string'))
