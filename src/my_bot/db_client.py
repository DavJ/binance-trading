import datetime
import aiosqlite
import sqlite3
import json

from basic_tools import CONFIGURATION

def create_assets_table():
       try:
           with sqlite3.connect(CONFIGURATION.DB_FILE) as conn:
                conn.execute('''CREATE TABLE assets
                              (id INTEGER AUTOINCREMENT,
                              currency TEXT NOT NULL,
                              asset_amount_free REAL,
                              asset_amount_locked REAL,
                              max_amount REAL,
                              last_update_time TEXT,        
                              PRIMARY KEY (currency)
                              );''')
       except:
           print('cannot create  table assets')


def create_volatility_table():
    try:
        with sqlite3.connect(CONFIGURATION.DB_FILE) as conn:
            conn.execute('''CREATE TABLE volatility
                              (id INTEGER AUTOINCREMENT,
                               currency TEXT NOT NULL,
                               base_currency TEXT NOT NULL
                               time TEXT NOT NULL,
                               ratio REAL,                                    /*actual currency to base currency ratio*/
                               predicted_ratio REAL,                          /*predicted ratio in one time step*/
                               volatility REAL,                                  
                               last_update_time TEXT,        
                               PRIMARY KEY (currency, base_currency, time)
                              );''')
    except:
        print('cannot create table volatility')


def create_trades_table():
    try:
        with sqlite3.connect(CONFIGURATION.DB_FILE) as conn:
            conn.execute('''CREATE TABLE trades
                              (id INTEGER AUTOINCREMENT,
                               pair TEXT NOT NULL,
                               create_time TEXT NOT NULL,
                               side TEXT NOT NULL,
                               from_currency TEXT NOT NULL,
                               to_currency TEXT NOT NULL,
                               type TEXT NOT NULL,
                               average REAL,
                               price REAL,
                               executed REAL,
                               total REAL,
                               total_currency TEXT NOT NULL
                               ratio REAL,                                    
                               predicted_ratio REAL,                          
                               status TEXT NOT NULL,        
                               PRIMARY KEY (pair, create_time, side)
                              );''')
    except:
        print('cannot create table trades')



def get_count_of_assets():
    with sqlite3.connect(CONFIGURATION.DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT count(*) FROM assets;')
        return cursor.fetchone()[0]

def get_asset(currency):
    with sqlite3.connect(CONFIGURATION.DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT *
                          FROM assets
                          WHERE currency=?;''',
                       (currency,))
        try:
            return json.loads(cursor.fetchone()[0])
        except Exception:
            return None

if __name__ == '__main__':
    try:
        create_assets_table()
        create_volatility_table()
        create_trades_table()
    except Exception:
        print('cannot create table')
