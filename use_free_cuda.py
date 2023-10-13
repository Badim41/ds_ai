import asyncio
import configparser

config = configparser.ConfigParser()


def set_get_config_all(key, value=None):
    config.read('config.ini')
    if value is None:
        return config.get("Values", key)
    config.set("Values", key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def set_get_config_all_async(key, value=None):
    config.read('config.ini')
    if value is None:
        return config.get("Values", key)
    config.set("Values", key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


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


async def use_cuda_async(index=None):
    if not index is None:
        await set_get_config_all_async(f"cuda{index}_is_busy", True)
        return
    while True:
        if not await set_get_config_all_async("cuda0_is_busy"):
            await set_get_config_all_async("cuda0_is_busy", True)
            return 0
        if not await set_get_config_all_async("cuda1_is_busy"):
            await set_get_config_all_async("cuda0_is_busy", True)
            return 1


async def wait_for_cuda_async(suffix=None):
    if suffix == "All":
        while True:
            if not await set_get_config_all_async("cuda0_is_busy"):
                if not await set_get_config_all_async("cuda1_is_busy"):
                    return
            await asyncio.sleep(0.1)
    while True:
        if not await set_get_config_all_async("cuda0_is_busy"):
            return 0
        if not await set_get_config_all_async("cuda1_is_busy"):
            return 1
        await asyncio.sleep(0.1)


def stop_use_cuda(index):
    set_get_config_all(f"cuda{index}_is_busy", False)


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
