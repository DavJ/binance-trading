import datetime
import aiosqlite
import sqlite3
import json

from basic_tools import CONFIGURATION

def create_table():
       try:
           with sqlite3.connect(CONFIGURATION.DB_FILE) as conn:
                conn.execute('''CREATE TABLE assets
                              (currency TEXT NOT NULL,
                              price REAL,
                              asset_amount REAL,
                              asset_amount_available REAL,
                              asset_amount_in_stable_currency REAL
                              max_amount REAL,
                              last_update_time TEXT,        
                              PRIMARY KEY (currency)
                              );''')
       except:
           print('cannot create table')

async def aio_insert_asset(currency=None, price=None, asset_amount=None, asset_amount_available=None,
                           asset_amount_in_stable_currency=None, max_amount=None):
        insert_sql = '''
        INSERT INTO assets (currency, price, asset_amount_total, asset_amount_available, asset_amount_in_stable_currency,
        max_amount, last_update_time) VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H-%M','now')) ;
        '''
        async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
            asset = (currency, price, asset_amount, asset_amount_available, asset_amount_in_stable_currency, max_amount)
            await conn.execute(insert_sql, asset)
            await conn.commit()

async def aio_update_asset(currency=None, price=None, asset_amount=None, asset_amount_available=None,
                           asset_amount_in_stable_currency=None, max_amount=None):
    update_sql = '''
        UPDATE assets 
        SET price=?, asset_amount=?, asset_amount_available=?, asset_amount_in_stable_currency=?, max_amount=?, last_update_time=strftime('%Y-%m-%d %H-%M','now')
        WHERE currency=?;
        '''
    async with aiosqlite.connect(CONFIGURATION.DB_FILE) as conn:
        asset = (price, asset_amount, asset_amount_available, asset_amount_in_stable_currency, currency)
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
        create_table()
    except Exception:
        print('cannot create table')
