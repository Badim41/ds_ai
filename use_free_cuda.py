import asyncio
import time
from set_get_config import set_get_config_all_not_async, set_get_config_all


def use_cuda(index=None):
    if not index is None:
        set_get_config_all_not_async("Values", f"cuda{index}_is_busy", True)
        return
    while True:
        if not set_get_config_all_not_async("Values", "cuda0_is_busy"):
            set_get_config_all_not_async("Values", "cuda0_is_busy", True)
            return 0
        if not set_get_config_all_not_async("Values", "cuda1_is_busy"):
            set_get_config_all_not_async("Values", "cuda0_is_busy", True)
            return 1
        time.sleep(0.25)


async def use_cuda_async(index=None):
    if not index is None:
        await set_get_config_all("Values", f"cuda{index}_is_busy", True)
        return
    while True:
        if await set_get_config_all("Values", "cuda0_is_busy") == "False":
            await set_get_config_all("Values", "cuda0_is_busy", True)
            return 0
        if await set_get_config_all("Values", "cuda1_is_busy") == "False":
            await set_get_config_all("Values", "cuda0_is_busy", True)
            return 1
        await asyncio.sleep(0.25)


async def wait_for_cuda_async(suffix=None):
    if suffix == "All":
        while True:
            if await set_get_config_all("Values", "cuda0_is_busy") == "False":
                if await set_get_config_all("Values", "cuda1_is_busy") == "False":
                    return
            await asyncio.sleep(0.1)
    while True:
        if await set_get_config_all("Values", "cuda0_is_busy") == "False":
            return 0
        if await set_get_config_all("Values", "cuda1_is_busy") == "False":
            return 1
        await asyncio.sleep(0.1)


def stop_use_cuda(index):
    set_get_config_all_not_async("Values", f"cuda{index}_is_busy", False)


async def stop_use_cuda_async(index):
    await set_get_config_all("Values", f"cuda{index}_is_busy", False)


def check_cuda(index=None):
    if index is None:
        cuda_avaible = 0
        if not set_get_config_all_not_async("Values", "cuda0_is_busy"):
            cuda_avaible += 1
        if not set_get_config_all_not_async("Values", "cuda1_is_busy"):
            cuda_avaible += 1
        return cuda_avaible
    else:
        return set_get_config_all_not_async("Values", f"cuda{index}_is_busy")


async def check_cuda_async(index=None):
    if index is None:
        cuda_avaible = 0
        if await set_get_config_all("Values", "cuda0_is_busy") == "False":
            cuda_avaible += 1
        if await set_get_config_all("Values", "cuda1_is_busy") == "False":
            cuda_avaible += 1
        return cuda_avaible
    else:
        return await set_get_config_all("Values", f"cuda{index}_is_busy")


async def use_cuda_images(index=None):
    if not index is None:
        if await set_get_config_all(f"Image{index}", "model_loaded", None) == "True":
            await set_get_config_all(f"Image{index}", "model_loaded", "using")
            return
        else:
            raise "1-ая видеокарта занята"
    else:
        if await set_get_config_all(f"Image0", "model_loaded", None) == "True":
            return 0
        if await set_get_config_all(f"Image1", "model_loaded", None) == "True":
            return 1
        raise "Нет свободных видеокарт!"


async def check_cuda_images(index=None):
    if index is None:
        image_models_avaible = 0
        if await set_get_config_all(f"Image0", "model_loaded", None) == "True":
            image_models_avaible += 1
        if await set_get_config_all(f"Image1", "model_loaded", None) == "True":
            image_models_avaible += 1
        return image_models_avaible
    else:
        return await set_get_config_all(f"Image{index}", "model_loaded", None)


async def stop_use_cuda_images(index=None):
    if not index is None:
        await set_get_config_all(f"Image{index}", "model_loaded", "True")
    else:
        await set_get_config_all(f"Image0", "model_loaded", "True")
        await set_get_config_all(f"Image1", "model_loaded", "True")
