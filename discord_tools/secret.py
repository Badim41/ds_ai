import asyncio

from discord_tools.sql_db import set_get_database_async

class SecretKey:
    voice_keys = "voice_keys"
    gpt_keys = "gpt_keys"
    gpt_auth = "gpt_auth"

def create_secret(key:str, value:str):
    asyncio.run(set_get_database_async("secret", str(key), str(value)))

def load_secret(key:str):
    return asyncio.run(set_get_database_async("secret", str(key)))
