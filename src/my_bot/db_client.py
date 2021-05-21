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
                              asset_amount REAL,
                              asset_amount_available REAL,
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


async def aio_insert_asset(currency=None, asset_amount=None, asset_amount_available=None, max_amount=None):
        insert_sql = '''
        INSERT INTO assets (currency, asset_amount_total, asset_amount_available, max_amount, last_update_time)
        VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H-%M','now')) ;
        '''
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            asset = (currency, asset_amount, asset_amount_available, max_amount)
            await conn.execute(insert_sql, asset)
            await conn.commit()

async def aio_update_asset(id=None, asset_amount=None, asset_amount_available=None, max_amount=None):
    update_sql = '''
        UPDATE assets 
        SET asset_amount=?, asset_amount_available=?, max_amount=?, last_update_time=strftime('%Y-%m-%d %H-%M','now')
        WHERE id=?;
        '''
    async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
        asset = (asset_amount, asset_amount_available, max_amount, id)
        await conn.execute(update_sql, asset)
        await conn.commit()


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
