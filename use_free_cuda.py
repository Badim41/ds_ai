import asyncio
import configparser
import time

config = configparser.ConfigParser()


def set_get_config_all(key, value=None):
    try:
        config.read('config.ini')
        if value is None:
            return config.get("Values", key)
        config.set("Values", key, str(value))
        # Сохранение
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"Ошибка при чтении конфига:{e}")
        time.sleep(0.1)
        result = set_get_config_all(key, value)
        return result


async def set_get_config_all_async(key, value=None):
    try:
        config.read('config.ini')
        if value is None:
            return config.get("Values", key)
        config.set("Values", key, str(value))
        # Сохранение
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"Ошибка при чтении конфига:{e}")
        await asyncio.sleep(0.1)
        result = await set_get_config_all_async(key, value)
        return result


def use_cuda(index=None):
    if not index is None:
        set_get_config_all(f"cuda{index}_is_busy", True)
        return
    while True:
        if not set_get_config_all("cuda0_is_busy"):
            set_get_config_all("cuda0_is_busy", True)
            return 0
        if not set_get_config_all("cuda1_is_busy"):
            set_get_config_all("cuda0_is_busy", True)
            return 1
        time.sleep(0.25)


async def use_cuda_async(index=None):
    if not index is None:
        await set_get_config_all_async(f"cuda{index}_is_busy", True)
        return
    while True:
        if await set_get_config_all_async("cuda0_is_busy") == "False":
            await set_get_config_all_async("cuda0_is_busy", True)
            return 0
        if await set_get_config_all_async("cuda1_is_busy") == "False":
            await set_get_config_all_async("cuda0_is_busy", True)
            return 1
        await asyncio.sleep(0.25)


async def wait_for_cuda_async(suffix=None):
    if suffix == "All":
        while True:
            if await set_get_config_all_async("cuda0_is_busy") == "False":
                if await set_get_config_all_async("cuda1_is_busy") == "False":
                    return
            await asyncio.sleep(0.1)
    while True:
        if await set_get_config_all_async("cuda0_is_busy") == "False":
            return 0
        if await set_get_config_all_async("cuda1_is_busy") == "False":
            return 1
        await asyncio.sleep(0.1)


def stop_use_cuda(index):
    set_get_config_all(f"cuda{index}_is_busy", False)

async def stop_use_cuda_async(index):
    await set_get_config_all_async(f"cuda{index}_is_busy", False)


def check_cuda(index=None):
    if index is None:
        cuda_avaible = 0
        if not set_get_config_all("cuda0_is_busy"):
            cuda_avaible += 1
        if not set_get_config_all("cuda1_is_busy"):
            cuda_avaible += 1
        return cuda_avaible
    else:
        return set_get_config_all(f"cuda{index}_is_busy")

async def check_cuda_async(index=None):
    if index is None:
        cuda_avaible = 0
        if await set_get_config_all_async("cuda0_is_busy") == "False":
            cuda_avaible += 1
        if await set_get_config_all_async("cuda1_is_busy") == "False":
            cuda_avaible += 1
        return cuda_avaible
    else:
        return await set_get_config_all_async(f"cuda{index}_is_busy")
