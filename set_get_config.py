import asyncio
import configparser
import time

config = configparser.ConfigParser()

async def set_get_config_all(section, key, value=None):
    try:
        config.read('config.ini')
        if value is None:
            config.read('config.ini')
            return config.get(section, key)
        config.set(section, key, str(value))
        # Сохранение
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"Ошибка при чтении конфига:{e}")
        await asyncio.sleep(0.1)
        result = await set_get_config_all(section, key, value)
        return result

def set_get_config_all_not_async(section, key, value=None):
    try:
        config.read('config.ini')
        if value is None:
            config.read('config.ini')
            return config.get(section, key)
        config.set(section, key, str(value))
        # Сохранение
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"Ошибка при чтении конфига:{e}")
        time.sleep(0.1)
        result = set_get_config_all_not_async(section, key, value)
        return result