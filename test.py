import asyncio

from set_get_config import set_get_config_all


async def remove_unavaible_voice_token():
    tokens = (await set_get_config_all("voice", "avaible_tokens")).split(";")
    avaible_tokens = []
    if len(tokens) == 1:
        await set_get_config_all("voice", "avaible_tokens", "None")
        print("==БОЛЬШЕ НЕТ ТОКЕНОВ ДЛЯ СИНТЕЗА ГОЛОСА==")
        return
    skip_first = True
    for token in tokens:
        if skip_first:
            skip_first = False
            continue
        avaible_tokens.append(token)
    await set_get_config_all("voice", "avaible_tokens", ';'.join(avaible_tokens))


asyncio.run(remove_unavaible_voice_token())
