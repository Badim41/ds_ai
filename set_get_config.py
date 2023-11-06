import asyncio
import configparser
from aiofiles import open as aio_open
import threading
import time

config = configparser.ConfigParser()

config_lock = threading.Lock()


async def set_get_config_all(section, key, value=None, error=0):
    try:
        async with aio_open('config.ini', 'r') as f:
            config.read('config.ini', encoding='utf-8')
            if value is None:
                return config.get(section, key)
            config.set(section, key, str(value))
            async with aio_open('config.ini', 'w') as configfile:
                config.write(configfile)
    except Exception as e:
        if error == 5:
            raise f"Ошибка при чтении конфига со значениями: {section}, {key}, {value}.\n{e}"
        await asyncio.sleep(0.1)
        result = await set_get_config_all(section, key, value, error=error+1)
        return result

def set_get_config_all_not_async(section, key, value=None, error=0):
    try:
        with config_lock:
            config.read('config.ini', encoding='utf-8')
            if value is None:
                return config.get(section, key)
            config.set(section, key, str(value))
            with open('config.ini', 'w', encoding='utf-8') as configfile:
                config.write(configfile)
    except Exception as e:
        if error == 5:
            raise f"Ошибка при чтении конфига со значениями: {section}, {key}, {value}.\n{e}"
        time.sleep(0.1)
        result = set_get_config_all_not_async(section, key, value, error=error+1)
        return result