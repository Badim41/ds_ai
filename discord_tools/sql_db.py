import sqlite3
import asyncio
from contextlib import asynccontextmanager

db_path = 'config.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create a table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section TEXT,
        key TEXT NOT NULL UNIQUE,
        value TEXT
    )
''')
conn.commit()


@asynccontextmanager
async def database_lock():
    lock = asyncio.Lock()
    async with lock:
        yield lock


async def set_get_database_async(section, key, value=None):
    """
    не поддерживается массив секций!
    изменить - await set_get_database_async("test", keys, values)
    получить - await set_get_database_async("test", "500")
    """
    section = str(section)

    async with database_lock():
        # Create SQLite connection and cursor
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create a table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT,
                key TEXT NOT NULL UNIQUE,
                value TEXT
            )
        ''')
        conn.commit()

        # If both key and value are arrays, insert multiple key-value pairs
        if isinstance(key, list) and isinstance(value, list):
            data = [(section, str(k), str(v)) for k, v in zip(key, value)]
            cursor.executemany('INSERT OR REPLACE INTO config (section, key, value) VALUES (?, ?, ?)', data)
            conn.commit()
        else:
            key = str(key)

            # If value is not provided, fetch the value for the key
            if value is None:
                cursor.execute('SELECT value FROM config WHERE section = ? AND key = ?', (section, key))
                return_value = cursor.fetchone()
                return return_value[0] if return_value else None

            # Set the value for the key
            cursor.execute('INSERT OR REPLACE INTO config (section, key, value) VALUES (?, ?, ?)',
                           (section, key, str(value)))
            conn.commit()

        # Close the connection
        conn.close()


async def get_all_config_async():
    """
    returns massive of sections, keys and values

    :return: section, key, value
    """

    # Create SQLite connection and cursor
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all key-value pairs from the config table
    cursor.execute('SELECT section, key, value FROM config')
    result = cursor.fetchall()

    # Close the connection
    conn.close()

    return result


def get_database(section, key):
    section = str(section)
    key = str(key)

    # Создаем подключение к SQLite и курсор
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем значение для ключа
    cursor.execute('SELECT value FROM config WHERE section = ? AND key = ?', (section, key))
    return_value = cursor.fetchone()

    # Закрываем соединение
    conn.close()

    return return_value[0] if return_value else None


async def set_database(section, key, value):
    section = str(section)
    key = str(key)
    value = str(value)

    async with database_lock():
        # Создаем подключение к SQLite и курсор
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Создаем таблицу, если она не существует
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT,
                key TEXT NOT NULL UNIQUE,
                value TEXT
            )
        ''')
        conn.commit()

        # Устанавливаем значение для ключа
        cursor.execute('INSERT OR REPLACE INTO config (section, key, value) VALUES (?, ?, ?)', (section, key, value))
        conn.commit()

        # Закрываем соединение
        conn.close()


def set_database_not_async(section, key, value):
    section = str(section)
    key = str(key)
    value = str(value)
    # Создаем подключение к SQLite и курсор
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаем таблицу, если она не существует
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT,
                key TEXT NOT NULL UNIQUE,
                value TEXT
            )
        ''')
    conn.commit()

    # Устанавливаем значение для ключа
    cursor.execute('INSERT OR REPLACE INTO config (section, key, value) VALUES (?, ?, ?)', (section, key, value))
    conn.commit()

    # Закрываем соединение
    conn.close()
