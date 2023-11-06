import asyncio
import configparser
import time

config = configparser.ConfigParser()

async def set_get_config_all(section, key, value=None, error=0):
    try:
        config.read('config.ini', encoding='utf-8')
        if value is None:
            return config.get(section, key)
        config.set(section, key, str(value))
        # Сохранение
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    except Exception as e:
        if error == 5:
            raise f"Ошибка при чтении конфига со значениями: {section}, {key}, {value}.\n{e}"
        await asyncio.sleep(0.1)
        result = await set_get_config_all(section, key, value, error=error+1)
        return result

def set_get_config_all_not_async(section, key, value=None, error=0):

    try:
        config.read('config.ini', encoding='utf-8')
        if value is None:
            return config.get(section, key)
        config.set(section, key, str(value))
        # Сохранение
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    except Exception as e:
        if error == 5:
            raise f"Ошибка при чтении конфига со значениями: {section}, {key}, {value}.\n{e}"
        time.sleep(0.1)
        result = set_get_config_all_not_async(section, key, value, error=error+1)
        return result