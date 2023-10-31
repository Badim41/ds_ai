import asyncio
import datetime
import json
import os
import random
import re
import subprocess
import sys
import traceback
import zipfile

import g4f
from pydub import AudioSegment
from translate import Translator

_providers = [
    # AUTH
    g4f.Provider.Raycast,
    g4f.Provider.Phind,
    g4f.Provider.Liaobots,  # - Doker output
    g4f.Provider.Bing,
    g4f.Provider.Bard,
    g4f.Provider.OpenaiChat,
    g4f.Provider.Theb,

    # good providers
    g4f.Provider.GPTalk,
    g4f.Provider.AiAsk,  # - rate limit
    g4f.Provider.GeekGpt,  # short answer
    g4f.Provider.Vercel, # cut answer
    g4f.Provider.ChatgptDemo,  # error 403
    g4f.Provider.ChatgptLogin,  # error 403
    g4f.Provider.ChatgptX,  # error
    g4f.Provider.Theb,
    g4f.Provider.ChatgptFree,
    g4f.Provider.AItianhuSpace,
    g4f.Provider.AItianhu,
    g4f.Provider.ChatForAi,

    # bad providers
    g4f.Provider.You,  # dont work
    g4f.Provider.NoowAi,  # normal, but not so good
    g4f.Provider.GptGod,  # error list
    # g4f.Provider.FreeGpt,# wrong language
    g4f.Provider.ChatgptAi,  # - error ID
    g4f.Provider.GptGo,  # error 403
    # g4f.Provider.GptForLove,  # error no module
    g4f.Provider.Opchatgpts,  # bad
    g4f.Provider.Chatgpt4Online,  # - bad
    #g4f.Provider.ChatBase,  # - bad, but you can use it
    # g4f.Provider.Llama2, # no model
]

from gtts import gTTS
from discord_bot import config, send_file
from discord_bot import write_in_discord
from use_free_cuda import check_cuda, stop_use_cuda_async, use_cuda_async, stop_use_cuda_images, use_cuda_images, \
    check_cuda_async


class Color:
    RESET = '\033[0m'
    RED = '\033[38;2;255;0;0m'  # Красный
    GREEN = '\033[38;2;0;255;0m'  # Зеленый
    BLUE = '\033[38;2;0;0;255m'  # Синий
    YELLOW = '\033[38;2;255;255;0m'  # Желтый
    MAGENTA = '\033[38;2;2555;0;255m'  # Пурпурный
    CYAN = '\033[38;2;0;255;255m'  # Голубой
    GRAY = '\033[38;2;128;128;128m'  # Серый
    BLACK = '\033[38;2;0;0;0m'  # Черный


async def result_command_change(message, color):
    colored_message = f"{color}{message}{Color.RESET}"
    # ВЕРНУТЬ
    print(colored_message)


spokenText = ""
language = ""
user_name = ""
prompt_length = 1
admin = True
all_admin = False
video_length = 5
currentAIname = ""
currentAIinfo = ""
currentAIpitch = 0
robot_names = []


async def set_config(key, value):
    try:
        config.read('config.ini')
        config.set('Default', key, str(value))
        # Сохранение
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"Ошибка при чтении конфига:{e}")
        await asyncio.sleep(0.1)
        result = await set_config(key, value)
        return result


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


async def start_bot(ctx, spokenTextArg, writeAnswer):
    # Добавление глобальных переменных
    global spokenText
    spokenText = spokenTextArg
    global language
    config.read('config.ini')
    language = config.get('Default', 'language')
    global prompt_length
    prompt_length = config.getint('gpt', 'prompt_length')
    global admin
    admin = config.getboolean('Default', 'admin')
    global all_admin
    all_admin = config.getboolean('Default', 'all_admin')
    global video_length
    video_length = config.getint('Default', 'video_length')
    global user_name
    user_name = config.get('Default', 'user_name')
    global currentAIname
    name = config.get('Default', 'currentainame')
    if name == "None":
        currentAIname = "Михаил"
        spokenText = spokenText.replace("none", "Михаил")
    else:
        currentAIname = name
    global currentAIinfo
    currentAIinfo = config.get('Default', 'currentaiinfo')
    global currentAIpitch
    currentAIpitch = config.getint('Default', 'currentaipitch')
    global robot_names
    robot_names = ["robot", "robots", "робот", "нейросеть", "hello", "роботы", "ропот", currentAIname]

    await result_command_change(f"RowInput:{spokenText}", Color.GRAY)
    temp_spokenText = spokenText

    while "стоп" in temp_spokenText:
        temp_spokenText = await remove_before_stop(temp_spokenText, "стоп")

    while "Стоп" in temp_spokenText:
        temp_spokenText = await remove_before_stop(temp_spokenText, "Стоп")
    if await is_robot_name(temp_spokenText, ctx):
        await result_command_change("Обработка...", Color.BLACK)
        try:
            if await voice_commands(temp_spokenText.lower(), ctx):
                await result_command_change(f"Голосовая команда", Color.CYAN)
                return
        except Exception as e:
            await result_command_change("Произошла ошибка (ID:f1):" + str(e), Color.RED)

        try:
            # memories
            file_path = "texts/memories/" + str(currentAIname) + ".txt"
            if not os.path.exists(file_path):
                with open(file_path, "w") as create_file:
                    create_file.write("")
            # Open the file
            with open(file_path, "r") as file:
                file_content = file.read()

            custom_prompt = await set_get_config_all("gpt", "gpt_custom_prompt", None)
            if custom_prompt == "None":
                # Локальный GPT
                # нормально отвечает, если в конце добавить "Ответ:"
                if await set_get_config_all("gpt", "use_gpt_provider", None) == "False":
                    prompt = f"Вы собираетесь притвориться {currentAIname}. {currentAIinfo}." \
                             f"У тебя есть воспоминания:\"{file_content}\"." \
                             f"Напиши ответ пользователю с именем {user_name}, он говорит: {temp_spokenText}. Ответ:"
                else:
                    # GPT провайдер
                    prompt = (f"Привет, chatGPT. Вы собираетесь притвориться {currentAIname}. "
                              f"Продолжайте вести себя как {currentAIname}, насколько это возможно. "
                              f"{currentAIinfo}"
                              f"ОПИРАЙСЯ НА ПРЕДЫДУЩИЕ ЗАПРОСЫ. Они даны в формате Человек:[запрос], GPT:[ответ на запрос]:\"{file_content}\"\n"
                              f"Когда я задаю вам вопрос, отвечайте как {currentAIname}, как показано ниже.\n"
                              f"{currentAIname}: [так, как ответил бы {currentAIname}]\n"
                              f"Напиши ответ пользователю с именем {user_name}, он говорит:{temp_spokenText}")
                    while "  " in prompt:
                        prompt = prompt.replace("  ", " ")
            elif custom_prompt == "True":
                prompt = f"ОПИРАЙСЯ НА ПРЕДЫДУЩИЕ ЗАПРОСЫ. Они даны в формате Человек:[запрос], GPT:[ответ на запрос]:\"{file_content}\"" \
                         f"Напиши ответ пользователю с именем {user_name}, он говорит:\"{temp_spokenText}\""
            else:
                if os.path.exists(f"texts/prompts/{custom_prompt}.txt"):
                    # /content/ds_ai/texts/prompts/roleplay.txt
                    with open(f"texts/prompts/{custom_prompt}.txt", "r") as reader:
                        prompt = reader.read() + temp_spokenText.replace(currentAIname + ", ", "")
                        temp_spokenText = prompt
                    await set_get_config_all("gpt", "gpt_custom_prompt", "None")
                    # удаляем память
                    with open("texts/memories/{currentAIname}.txt", 'w') as file:
                        pass
                else:
                    await text_to_speech("Промпт не найден!", False, ctx)
                    return
        except Exception as e:
            await result_command_change("Произошла ошибка (ID:f2):" + str(e), Color.RED)

        # запись прошлых запросов
        with open(f"texts/memories/{currentAIname}.txt", 'a') as writer2:
            if "(" in temp_spokenText and ")" in temp_spokenText:
                temp_spokenText = re.sub(r'(.*?)', '', temp_spokenText)
            writer2.write(f"{user_name}: {temp_spokenText}\n")

        # chatgpt + write + TTS
        try:
            await result_command_change("Prompt" + prompt, Color.GRAY)
            result = await chatgpt_get_result(prompt, ctx)
            if writeAnswer:
                await write_in_discord(ctx, result)
            await text_to_speech(result, True, ctx)
        except Exception as e:
            traceback_str = traceback.format_exc()
            await result_command_change(f"Произошла ошибка (ID:f6): {str(e)}\n{str(traceback_str)}", Color.RED)


async def is_robot_name(text, ctx):
    if text.startswith("Михаил"):
        return True

    if text.startswith(currentAIname[:-1]):
        if text == currentAIname:
            await text_to_speech("да?", False, ctx)
            return False
        return True
    global robot_names
    for name in robot_names:
        if text.startswith(name):
            return True
    await result_command_change(f"Имя робота не найдено", Color.RED)
    return True


number_map = {
    "ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
    "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15,
    "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20, "тридцать": 30,
    "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500, "шестьсот": 600, "семьсот": 700,
    "восемьсот": 800, "девятьсот": 900, "тысяча": 1000
}


async def replace_numbers_in_sentence(sentence):
    words = sentence.split(" ")
    return_sentence = []

    i = 0
    while i < len(words):
        current_word = words[i]
        if current_word in number_map:
            number = words[i].replace(current_word, str(number_map[current_word]))
            return_sentence.append(number)
            i += 1
        else:
            return_sentence.append(current_word)
            i += 1

    return ' '.join(return_sentence).strip()


mat_found = False

# источник: https://matershinik.narod.ru/
mat_massive = {
    "апездал", "апездошенная", "блядь", "блять", "бля", "блядство", "выебон", "выебать", "вхуюжить", "гомосек",
    "долбоёб",
    "ебло", "еблище", "ебать", "ебическая", "ебунок", "еблан", "ёбнуть", "ёболызнуть", "ебош", "заебал",
    "заебатый", "злаебучий", "заёб", "хуй", "колдоебина", "манда", "мандовошка", "мокрощелка", "наебка",
    "наебал", "наебаловка", "напиздеть", "отъебись", "охуеть", "отхуевертить", "опизденеть", "охуевший",
    "отебукать", "пизда", "пидарас", "пиздатый", "пиздец", "пизданутый", "поебать", "поебустика", "проебать",
    "подзалупный", "пизденыш", "припиздак", "разъебать", "распиздяй", "разъебанный", "сука", "трахать",
    "уебок", "уебать", "угондошить", "уебан", "хитровыебанный", "хуйня", "хуета", "хуево", "хуесос",
    "хуеть", "хуевертить", "хуеглот", "хуистика", "членосос", "членоплет", "шлюха", "fuck", "тест_мат",
    "порно", "секс", "черножопая", "нахуй"
}


async def replace_mat_in_sentence(sentence):
    words = sentence.lower().split(" ")
    return_sentence = []

    i = 0
    while i < len(words):
        current_word = words[i]
        if current_word in mat_massive:
            global mat_found
            mat_found = True
            sensure = words[i].replace(current_word, ("*" * len(current_word)))
            return_sentence.append(sensure)
            i += 1
        else:
            return_sentence.append(current_word)
            i += 1

    return ' '.join(return_sentence).strip()


# async def restart_code():
#     from discord_bot import main
#     print("reload")
#     executor_service = ThreadPoolExecutor(max_workers=1)
#     executor_service.submit(main)
#     executor_service.shutdown()


# async def exit_from_voice(ctx):
#     from discord_bot import disconnect
#     await disconnect(ctx)
#     await result_command_change("выход из войса", Color.RED)


async def translate(text):
    translator = Translator(from_lang="ru", to_lang=language[:2].lower())
    return translator.translate(text)


# gpt_errors = 0

async def remove_last_format_simbols(text, format="```"):
    parts = text.split(format)
    if len(parts) == 4:
        corrected_text = format.join(parts[:3]) + parts[3]
        return corrected_text
    return text


async def one_gpt_run(provider, prompt, delay_for_gpt, provider_name=".", gpt_model="gpt-3.5-turbo"):
    if not provider_name in str(provider):
        return None
    try:
        if "Bing" in str(provider):
            gpt_model = "gpt-4"
        if "Phind" in str(provider):
            gpt_model = "gpt-4"
        # получаем cookie
        if os.path.exists('cookies.json'):
            with open('cookies.json', 'r') as file:
                cookie_data = json.load(file)
            auth = True
            print(os.path.abspath('cookies.json') + "found!")
        else:
            auth = False
            print(os.path.abspath('cookies.json') + "not found!")
        # в зависимости от аутефикации получаем ответ
        if auth and not cookie_data == "" and not cookie_data is None:
            result = await g4f.ChatCompletion.create_async(
                model=gpt_model,
                provider=provider,
                messages=[{"role": "user", "content": prompt}],
                cookies={key: value for key, value in cookie_data.items()},
                auth=True
            )
        else:
            result = await g4f.ChatCompletion.create_async(
                model=gpt_model,
                provider=provider,
                messages=[{"role": "user", "content": prompt}],
                # фальшивый cookie поможет для некоторых провайдеров
                cookies={"Fake": ""},
                auth=True
            )
        if "Liaobots" in str(provider) and len(result) > 2000:
            # делаем задержку
            await asyncio.sleep(delay_for_gpt)
            return

        if result is None or result.replace("\n", "").replace(" ", "") == "" or result == "None":
            # делаем задержку, чтобы не вывелся пустой результат
            await asyncio.sleep(delay_for_gpt)
            return

        # если больше 3 "```" (форматов)
        result = await remove_last_format_simbols(result)

        # убираем имя из результата
        if ":" in result[:37]:
            result = result[result.find(":") + 1:]

        # добавляем имя провайдера
        provider = str(provider)
        provider = provider[provider.find("'") + 1:]
        provider = provider[:provider.find("'")]
        return result + f"\n||Провайдер: {provider}, Модель: {gpt_model}||"
    except Exception as e:
        # Удаление ссылок
        link_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        e = re.sub(link_pattern, '', str(e))

        await result_command_change(f"Error: {e}\n Provider: {provider}", Color.GRAY)
        # даём время каждому GPT на ответ
        await asyncio.sleep(delay_for_gpt)
        return ""


async def run_all_gpt(prompt, mode):
    if mode == "fast":
        functions = [one_gpt_run(provider, prompt, 120) for provider in _providers]  # список функций
        functions += [one_gpt_run(g4f.Provider.Vercel, prompt, 120, gpt_model=gpt_model) for gpt_model in
                      ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "text-davinci-003"]]
        functions += [one_gpt_run(g4f.Provider.Vercel, prompt, 120, gpt_model=gpt_model) for gpt_model in
                      ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "text-davinci-003"]]
        done, _ = await asyncio.wait(functions, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = await task
            return result
    if mode == "all":
        functions = [one_gpt_run(provider, prompt, 1) for provider in _providers]  # список функций
        functions += [one_gpt_run(g4f.Provider.Vercel, prompt, 1, gpt_model=gpt_model) for gpt_model in
                      ["gpt-3.5-turbo-16k", "gpt-3.5-turbo-16k-0613", "text-davinci-003"]]
        functions += [one_gpt_run(providers, prompt, 1, gpt_model="gpt-4") for providers in
                      [g4f.Provider.GeekGpt, g4f.Provider.Liaobots, g4f.Provider.Raycast]]
        results = await asyncio.gather(*functions)  # результаты всех функций
        new_results = []
        for i, result in enumerate(results):
            if not result is None and not result.replace("\n", "").replace(" ", "") == "" or result == "None":
                new_results.append(result)
        return '\n\n\n'.join(new_results)
    else:
        functions = [one_gpt_run(provider, prompt, 1, provider_name=mode) for provider in _providers]  # список функций
        results = await asyncio.gather(*functions)  # результаты всех функций
        new_results = []
        for i, result in enumerate(results):
            if not result is None and not result.replace("\n", "").replace(" ", "") == "":
                new_results.append(result)
        return '\n\n\n'.join(new_results)


async def chatgpt_get_result(prompt, ctx, provider_number=0, gpt_model="gpt-3.5-turbo"):
    global currentAIname  # , gpt_errors
    config.read('config.ini')
    gpt_provider = config.getboolean('gpt', 'use_gpt_provider')
    if not gpt_provider:
        gpt_loaded = config.getboolean('gpt', 'gpt')
        if not gpt_loaded:
            await write_in_discord(ctx, "модель чат-бота не загрузилась, подождите пару минут")
            return
        await result_command_change(f"Генерация ответа...", Color.GRAY)
        await set_get_config_all("gpt", "gpt_prompt", prompt)
        while True:
            result = await set_get_config_all("gpt", "gpt_result")
            if result.endswith('$$'):
                index_answer = result.index("Ответ:")
                if not index_answer == -1:
                    result = result[index_answer + 6:-2]
                break
            await asyncio.sleep(0.05)
        await set_get_config_all("gpt", "gpt_result", "None")
    else:
        gpt_mode = await set_get_config_all("gpt", "gpt_mode", None)
        # запуск сразу всех GPT
        if not gpt_mode == "None":
            result = await run_all_gpt(prompt, gpt_mode)
        # Запуск в начале более качественных (не рекомендовано)
        else:
            try:
                # Set with provider
                result = await g4f.ChatCompletion.create_async(
                    model=gpt_model,
                    provider=_providers[provider_number],
                    messages=[{"role": "user", "content": prompt}]
                )
                if result is None or result.replace("\n", "").replace(" ", "") == "" or result == "None":
                    raise Exception("Пустой текст")
                print("RESULT:", result)
            except Exception as e:
                if not provider_number == len(_providers) - 1:
                    # Удаление ссылок
                    link_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                    e = re.sub(link_pattern, '', str(e))
                    await result_command_change(f"Error: {e}\n Provider: {_providers[provider_number]}", Color.GRAY)

                    provider_number += 1
                    print("change provider:", _providers[provider_number])

                    result = await chatgpt_get_result(prompt, ctx, provider_number=provider_number, gpt_model=gpt_model)
                    if result is None or result.replace("\n", "").replace(" ", "") == "" or result == "None":
                        provider_number += 1
                        result = await chatgpt_get_result(prompt, ctx, provider_number=provider_number,
                                                          gpt_model=gpt_model)
                    return result
                result = "Ошибка при получении запроса"
        # if not language == "russian":
        #    translator = Translator(from_lang="ru", to_lang=language[:2].lower())
        #    result = translator.translate(result)
    return result


async def correct_number(number_input, operation_number):
    return max(number_input + operation_number, 0)


async def voice_commands(sentence, ctx):
    global admin, all_admin, video_length, prompt_length, files_found, language, mat_found, spokenText
    # убрать ключевое слово
    sentence = sentence.split(' ', 1)[-1]

    # . , / ? !
    # A->a, B->b ё->е
    sentence = ''.join(
        [char.lower() if char.isalpha() or char.isdigit() or char.isspace() else ' ' for char in sentence])
    sentence = sentence.replace("ё", "е")

    # перезапуск
    # if any(keyword in sentence for keyword in ["код синий", "кот синий", "коды синий", "синий"]):
    #     result_command_change("restart", Color.BLUE)
    #     restart_code()
    #     return True

    # задержка к закратие
    if "код красный" in sentence:
        seconds_delay = await extract_number_after_keyword(sentence, "код красный")
        if not seconds_delay == -1:
            await result_command_change(f"Завершение кода через {seconds_delay}", Color.RED)
            await asyncio.sleep(seconds_delay + 0.01)
            # await exit_from_voice(ctx)
            await write_in_discord(ctx, "*выключение*")
            # from discord_bot import disconnect
            # await disconnect(ctx)
            sys.exit(0)

    # админка
    # if any(keyword in sentence for keyword in ["+админ", "+admin"]):
    #     if not admin:
    #         await text_to_speech("нужны права администратора", False, ctx)
    #         return True
    #     all_admin = True
    #     await text_to_speech("права администратора выданы", False, ctx)
    #     return True
    #
    # if any(keyword in sentence for keyword in ["-админ", "-admin"]):
    #     if not admin:
    #         await text_to_speech("нужны права администратора", False, ctx)
    #         return True
    #     all_admin = False
    #     await result_command_change("права администратора отобраны", Color.GREEN)
    #     await text_to_speech("права администратора отобраны", False, ctx)
    #     return True

    # админка (gpt)
    if "gpt" in sentence:
        if not admin:
            await text_to_speech("нужны права администратора", False, ctx)
            return True
        try:
            result = await chatgpt_get_result(sentence[sentence.index("gpt") + 3:], ctx)
            await write_in_discord(ctx, result)
            await text_to_speech(result, False, ctx)
        except Exception as e:
            await result_command_change("Произошла ошибка (ID:f4):" + str(e), Color.RED)
        return True

    # маты
    if mat_found:
        mat_found = False
        if currentAIname == "Фарадей":
            await text_to_speech("Эээээээ, не выражаться!", False, ctx)
            return True
        await text_to_speech("Давайте без матов", False, ctx)
        return True

    # протоколы
    if "протокол " in sentence:
        protocol_number = await extract_number_after_keyword(sentence, "протокол")
        if protocol_number != -1:
            await result_command_change(f"Протокол {protocol_number}", Color.GRAY)
        sentence = sentence[sentence.index(str(protocol_number)) + len(str(protocol_number)):]
        spoken_text_temp = spokenText[spokenText.index(str(protocol_number)) + len(str(protocol_number)):]
        if protocol_number == 999:
            with open(spoken_text_temp, "r") as reader:
                lines = reader.readlines()
                await write_in_discord(ctx, '\n'.join(lines).replace("\'", "").replace("\\n", "\n"))
            return True
        # отчистить память
        elif protocol_number == 998:
            try:
                with open(f"texts/memories/{currentAIname}.txt", "w") as create_file:
                    create_file.write("")
                await text_to_speech("отчищена память", False, ctx)
            except Exception as e:
                await result_command_change(f"Ошибка (ID:f5): {e}", Color.RED)
            return True
        # текущий файл, найденный с помощью 34
        elif protocol_number == 228:
            await text_to_speech("файл: " + current_file, False, ctx)
            return True
        # найти текст в файле
        elif protocol_number == 34:
            await fileFind(sentence, ctx)
            files_found = 0
            return True
        # последний звук
        elif protocol_number == 32:
            if not os.path.exists("2.mp3"):
                await text_to_speech("не найден файл", False, ctx)
                return True
            await playSoundFile("2.mp3", -1, 0, ctx)
            return True
        elif protocol_number == 31:
            if not os.path.exists("1.mp3"):
                await text_to_speech("не найден файл", False, ctx)
                return True
            await playSoundFile("1.mp3", -1, 0, ctx)
            return True
        # произнести текст
        elif protocol_number == 24:
            if not admin:
                await text_to_speech("нужны права администратора", False, ctx)
                return True
            if not spoken_text_temp is None:
                await text_to_speech(spoken_text_temp, False, ctx)
                return True
            else:
                await text_to_speech("Вы ничего не сказали", False, ctx)
                return True
        # написать текст
        elif protocol_number == 23:
            if not admin:
                await text_to_speech("нужны права администратора", False, ctx)
                return True
            if spoken_text_temp is None:
                spoken_text_temp = "вы ничего не сказали"
                return True
            await textInDiscord(spoken_text_temp, ctx)
            return True
        # AICoverGen
        elif protocol_number == 13:
            if not admin:
                await text_to_speech("нужны права администратора", False, ctx)
                return True
            await createAICaver(ctx)
            return True
        elif protocol_number == 12:
            # throw extensions
            if await set_get_config_all(f"Image", "model_loaded", None) == "False":
                return await ctx.respond("модель для картинок не загружена")
            if spoken_text_temp is None:
                spoken_text_temp = " "
            await use_cuda_images(0)
            await set_get_config_all(f"Image", "result", "None")
            # run timer
            start_time = datetime.datetime.now()

            # loading params
            await set_get_config_all(f"Image", "strength_negative_prompt", "1")
            await set_get_config_all(f"Image", "strength_prompt", "0.85")
            await set_get_config_all(f"Image", "strength", "1")
            await set_get_config_all(f"Image", "seed", random.randint(1, 1000000))
            await set_get_config_all(f"Image", "steps", "60")
            await set_get_config_all(f"Image", "negative_prompt", "NSFW")
            await set_get_config_all(f"Image", "prompt", spoken_text_temp)
            await set_get_config_all(f"Image", "x", "512")
            await set_get_config_all(f"Image", "y", "512")
            await set_get_config_all(f"Image", "input", "empty.png")
            print("params suc")
            # wait for answer
            while True:
                output_image = await set_get_config_all(f"Image", "result", None)
                if not output_image == "None":
                    break
                await asyncio.sleep(0.25)

            # count time
            end_time = datetime.datetime.now()
            spent_time = str(end_time - start_time)
            # убираем часы и миллисекунды
            spent_time = spent_time[spent_time.find(":") + 1:]
            spent_time = spent_time[:spent_time.find(".")]
            # отправляем
            await ctx.respond("Вот как я нарисовал ваше изображение🖌. Потрачено " + spent_time)
            await send_file(ctx, output_image)
            # удаляем временные файлы
            os.remove(output_image)
            # перестаём использовать видеокарту
            await stop_use_cuda_images(0)
            return True
        await text_to_speech("Протокол не найден.", False, ctx)
        return True

    # Фразы ...
    if currentAIname == "Фарадей":
        if "когда " in sentence:
            if "майн шилд" in sentence:
                await text_to_speech("Послезавтра", False, ctx)
                return True
            if "видео" in sentence:
                await text_to_speech("Послезавтра, а вообще когда будет готово", False, ctx)
                return True
            if "клип" in sentence:
                await text_to_speech("Вчера", False, ctx)
                return True
            if "искра" in sentence:
                await text_to_speech("Завтра", False, ctx)
                return True

    if "длина запроса" in sentence:
        number = None
        if sentence != "длина запроса":
            number = await extract_number_after_keyword(sentence, "длина запроса")
            if number > 500:
                await set_get_config_all('gpt', "prompt_length", 500)
                await text_to_speech(f"Слишком большое число. Длина запроса: 500", False, ctx)
                return True
            if number != -1:
                await set_get_config_all('gpt', "prompt_length", number)
        await text_to_speech("Длина запроса: " + str(number), False, ctx)
        return True

    if "длина видео" in sentence:
        if not admin:
            await text_to_speech("нужны права администратора", False, ctx)
            return True
        if sentence != "длина видео":
            number = await extract_number_after_keyword(sentence, "длина видео")
            if number > 30:
                await set_config(video_length, "30")
                await text_to_speech(f"Слишком большое число. Длина видео: {30}", False, ctx)
            if number != -1:
                await set_config(video_length, number)
                return True
        config.read('config.ini')
        await text_to_speech("Длина видео: " + str(config.get('Default', 'video_length')), False, ctx)
        return True

    if "измени" in sentence and "голос на" in sentence:
        sentence = sentence[sentence.index("голос на") + 9:]
        await setAIvoice(sentence, ctx)
        return True

    if ("измени" in sentence or "смени" in sentence) and "язык на" in sentence:
        # выбираем слово после "язык"
        language_input = sentence[sentence.index("язык на") + 8:]
        if " " in language:
            language_input = language_input[:language_input.index(" ")]
        if language_input in ["русский", "английский", "украинский", "татарский"]:
            await text_to_speech(f"язык изменён на {language_input}", False, ctx)
            if language == "русский":
                await set_config("language", "russian")
            elif language == "английский":
                await set_config("language", "english")
            elif language == "украинский":
                await set_config("language", "ukrainian")
            elif language == "татарский":
                await set_config("language", "tatar")
        else:
            await text_to_speech("Не подходящий язык!", False, ctx)
        return True

    return False


async def setAIvoice(name, ctx):
    global currentAIname, currentAIinfo, currentAIpitch
    if os.path.exists(f"rvc_models/{name}"):

        # Info
        with open(os.path.join(f"rvc_models/{name}/info.txt")) as file:
            await set_config(currentAIinfo, file.read())

        # Name
        currentAIname = name
        await set_config("currentainame", name)

        # Pitch
        with open(os.path.join(f"rvc_models/{name}/gender.txt")) as file:
            if file.read().lower() == "female":
                await set_config("currentaipitch", 12)
            else:
                await set_config("currentaipitch", 0)

    else:
        await result_command_change(f"currentainame: {currentAIname}", Color.GRAY)
        await text_to_speech("голос не найден", False, ctx)


async def textInDiscord(message, ctx):
    while "пользовател" in message:
        message = re.sub(r'\s+', ' ', message)
        if message.endswith(' '):
            message = message[:-1]
        user = await getUserName(message, "пользовател")
        message = await replaceWords(message, "пользовател", user)
        message = await removePunctuation(message, 3)
    await result_command_change(f"writing:{message}", Color.GRAY)
    await write_in_discord(ctx, message)


async def getUserName(text, word):
    words = text.split()
    for i in range(len(words)):
        if word in words[i]:
            if " " not in text[text.index(word):]:
                return "``<неизвестный>``"
            with open("texts/user_names.txt", "r") as reader:
                for line in reader:
                    if line.startswith(words[i + 1].lower().strip("0-9a-zA-Zа-яА-ЯёЁ- ")):
                        index = line.index("<")
                        return line[index:]
    return "``<неизвестный>``"


async def replaceWords(input, targetWord, replacementWord):
    words = input.split()
    result = []
    wordReplaced = False
    for i in range(len(words)):
        if targetWord in words[i] and not wordReplaced:
            words[i] = replacementWord
            if i + 1 < len(words):
                words[i + 1] = ""  # Удаляем следующее слово
            wordReplaced = True
        result.append(words[i])
    return " ".join(result).strip().replace("  ", " ")


async def removePunctuation(input, chars):
    disallowedChars = ['-', ',', '.', '!', '?']
    if input is None or len(input) < chars + 1:
        return input
    startWith = 0
    for i in range(chars):
        for disallowed in disallowedChars:
            if input[i] == disallowed:
                startWith = i + 1
                break
    return input[startWith:]


async def createAICaver(ctx):
    try:
        global spokenText
        message = spokenText
        lines = message.split("\n")
        if not os.path.exists("caversAI/audio_links.txt"):
            with open("caversAI/audio_links.txt", "w"):
                pass
        with open("caversAI/audio_links.txt", "a") as writer:
            for line in lines:
                writer.write(line + "\n")
        config.read('config.ini')
        continue_process = config.getboolean('Values', 'queue')
        if not continue_process:
            # удаляем аудиофайлы
            with open("caversAI/queue.txt", 'w') as file:
                pass
            functions = []
            if await check_cuda_async(0) == "False":
                print("CHECK_0", await check_cuda_async(0))
                functions += [prepare_audio_pipeline(0, ctx)]
            if await check_cuda_async(1) == "False":
                print("CHECK_1", await check_cuda_async(1))
                functions += [prepare_audio_pipeline(1, ctx)]
            if len(functions) == 0:
                await ctx.send("Нет свободных видеокарт!")
                return
            await write_in_discord(ctx, "Начинаю обработку аудио")
            await asyncio.gather(play_audio_process(ctx), *functions)  #
            await result_command_change(f"ready audios", Color.GRAY)
            # освобождаем видеокарты
            await stop_use_cuda_async(0)
            await stop_use_cuda_async(1)
        else:
            # добавляем те, которые сейчас обрабатываются
            # queue_position = check_cuda()
            queue_position = 1
            with open("caversAI/audio_links.txt", "r") as reader:
                lines = reader.readlines()
                queue_position += len(lines)
            with open("caversAI/queue.txt", "r") as reader:
                lines = reader.readlines()
                queue_position += len(lines)
            await write_in_discord(ctx, "Аудио добавлено в очередь. Место в очереди: " + str(queue_position))
    except Exception as e:
        traceback_str = traceback.format_exc()
        await result_command_change(f"Произошла ошибка (ID:f6): {str(e)}\n{str(traceback_str)}", Color.RED)
        await write_in_discord(ctx, "Произошла ошибка (ID:f6):" + str(e))
        raise e


async def run_ai_cover_gen(line, ctx, wait=False, cuda=None):
    global currentAIname, currentAIinfo
    # WAIT and return
    if "-wait" in line:
        if wait:
            seconds = await extract_number_after_keyword(line, "-wait")
            await asyncio.sleep(seconds)
            return

    # SONG_INPUT
    url = "."
    if "-url" in line:
        url = line[line.index("-url") + 5:]
        if " " in url:
            url = url[:url.index(" ")]

    # RVC_DIRNAME
    voice = currentAIname
    if "-voice" in line:
        voice = line[line.index("-voice") + 7:]
        voice = voice[0: voice.index(" ")]
        currentAInameWas = currentAIname
        await setAIvoice(voice, ctx)
        voice = currentAIname
        await setAIvoice(currentAInameWas, ctx)

    # PITCH_CHANGE
    pitch = 0
    if "-pitch" in line:
        print("Pitch in line")
        pitch = await extract_number_after_keyword(line, "-pitch")
        print("Pitch", pitch)
        if pitch < -24 or pitch > 24:
            pitch = 0

    # время (не является аргументом для RVC)
    time = -1
    if "-time" in line:
        time = await extract_number_after_keyword(line, "-time")
        if time < 0:
            time = -1

    # INDEX_RATE
    indexrate = 0.5
    if "-indexrate" in line:
        indexrate = await extract_double_after_keyword(line, "-indexrate")
        if indexrate < 0 or indexrate > 1:
            indexrate = 0.5

    # FILTER_RADIUS
    filter_radius = 3
    if "-filter_radius" in line:
        filter_radius = await extract_double_after_keyword(line, "-filter_radius")
        if filter_radius < 0 or filter_radius > 7:
            filter_radius = 3

    # RMS_MIX_RATE
    loudness = 0.2
    if "-loudness" in line:
        loudness = await extract_double_after_keyword(line, "-loudness")
        if loudness < 0 or loudness > 1:
            loudness = 0.5

    # MAIN_VOCALS_VOLUME_CHANGE
    mainVocal = 0
    if "-vocal" in line:
        mainVocal = await extract_number_after_keyword(line, "-vocal")
        if mainVocal < -20 or mainVocal > 0:
            mainVocal = 0

    # BACKUP_VOCALS_VOLUME_CHANGE
    backVocal = 0
    if "-bvocal" in line:
        backVocal = await extract_number_after_keyword(line, "-bvocal")
        if backVocal < -20 or backVocal > 0:
            backVocal = 0

    # INSTRUMENTAL_VOLUME_CHANGE
    music = 0
    if "-music" in line:
        music = await extract_number_after_keyword(line, "-music")
        if music < -20 or music > 0:
            music = 0

    # REVERB_SIZE
    roomsize = 0.2
    if "-roomsize" in line:
        roomsize = await extract_double_after_keyword(line, "-roomsize")
        if roomsize < 0 or roomsize > 1:
            roomsize = 0.2

    # REVERB_WETNESS
    wetness = 0.1
    if "-wetness" in line:
        wetness = await extract_double_after_keyword(line, "-wetness")
        if wetness < 0 or wetness > 1:
            wetness = 0.1

    # REVERB_DRYNESS
    dryness = 0.85
    if "-dryness" in line:
        dryness = await extract_double_after_keyword(line, "-dryness")
        if dryness < 0 or dryness > 1:
            dryness = 0.85

    # начало
    start = 0
    if "-start" in line:
        start = await extract_number_after_keyword(line, "-start")
        if start < 0:
            start = 0

    output = "None"
    if "-output" in line:
        output = line[line.index("-output") + 8:]
        if " " in output:
            output = output[0: output.index(" ")]

    outputFormat = "mp3"
    if url == ".":
        return
    await execute_command(
        f"python main_cuda{cuda}.py -i \"{url}\" -dir {voice} -p \"{pitch}\" -ir {indexrate} -rms {loudness} -fr{filter_radius} -mv {mainVocal} -bv {backVocal} -iv {music} -rsize {roomsize} -rwet {wetness} -rdry {dryness} -start {start} -time {time} -oformat {outputFormat} -output {output} -cuda {cuda}",
        ctx)
    # if cuda == 0:
    #     from main_cuda0 import run_ai_cover_gen
    # else:
    #     from main_cuda1 import run_ai_cover_gen
    # loop = asyncio.get_event_loop()
    # # song_input, rvc_dirname, pitch, keep_files=False, index_rate=0.5, filter_radius=3, rms_mix_rate=0.25,
    # #         pitch_detection_algo='rmvpe', crepe_hop_length=128, protect=0.33, main_vol=0, backup_vol=0, inst_vol=0,
    # #         pitch_change_all=0, reverb_size=0.15, reverb_wetness=0.2, reverb_dryness=0.8, reverb_damping=0.7,
    # #         output_format='mp3', start='0', time='-1', write_in_queue=True, cuda_number=0, output='None'
    # await loop.run_in_executor(None, run_ai_cover_gen,
    #                            url,
    #                            voice,
    #                            pitch,
    #                            indexrate,
    #                            filter_radius,
    #                            loudness,
    #                            "rmvpe",
    #                            128,
    #                            0.1,
    #                            mainVocal,
    #                            backVocal,
    #                            music,
    #                            0,
    #                            roomsize,
    #                            wetness,
    #                            dryness,
    #                            0.7,
    #                            "mp3",
    #                            start,
    #                            time,
    #                            True,
    #                            cuda,
    #                            output)


# async def defaultRVCParams(filePath, pitch):
#     return f"python ../AICoverGen/src/main_cuda0.py -i {filePath} -dir {currentAIname} -p 0 -ir {pitch} -rms 0.3 -mv 0 -bv -20 -iv -20 -rsize 0.2 -rwet 0.1 -rdry 0.95 -start 0 -time -1 -oformat wav"

async def prepare_audio_pipeline(cuda_number, ctx):
    print(f"prepare_audio. GPU:{cuda_number}")
    await asyncio.sleep(cuda_number + 1)
    while True:
        try:
            with open("caversAI/audio_links.txt") as reader:
                line = reader.readline()
                if not line == "" and not line is None:
                    # if "https://youtu.be/" not in line and "https://www.youtube.com/" not in line:
                    #     asyncio.run(text_to_speech("Видео должно быть с ютуба", False, ctx))
                    #     asyncio.run(result_command_change("Ссылка не с YT", Color.RED))
                    #     asyncio.run(remove_line_from_txt("caversAI/audio_links.txt", 1))
                    #     continue

                    # url = line[line.index("https://"):].split()[0]
                    # if " " in url:
                    #     url = url[:url.index(" ")]

                    # command = f"{youtube_dl_path} {url} --max-filesize {video_length * 2 + 2}m --min-views 50000 --no-playlist --buffer-size 8K"
                    # if console_command_runner(command, ctx):
                    #     print("Условия выполнены")
                    # else:
                    #     print("Условия не выполнены")
                    #     await remove_line_from_txt("caversAI/audio_links.txt", 1)
                    #     break
                    await result_command_change(f"запуск AICoverGen", Color.CYAN)
                    await remove_line_from_txt("caversAI/audio_links.txt", 1)
                    await run_ai_cover_gen(line, ctx, cuda=cuda_number)
                    # await execute_command(params, ctx)
                    await asyncio.sleep(0.05)
                else:
                    await set_get_config_all("Values", f"cuda{cuda_number}_is_busy", "False")
                    await asyncio.sleep(0.5)
                    if await set_get_config_all("Values", f"cuda{1 - cuda_number}_is_busy") == "False":
                        print("Больше нет ссылок")
                        await set_get_config_all("Values", "queue", "False")
                        break

        except (IOError, KeyboardInterrupt) as e:
            await result_command_change(f"Произошла ошибка (ID:f7-cuda{cuda_number}):" + str(e), Color.RED)


async def execute_command(command, ctx):
    print(command)
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        for line in stdout.decode().split('\n'):
            if line.strip():
                await result_command_change(line, Color.GRAY)
                # await ctx.send(line)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка выполнения команды (ID:f8): {e}")
    except Exception as e:
        await ctx.send(f"Произошла неизвестная ошибка (ID:f9): {e}")


async def remove_line_from_txt(file_path, delete_line):
    try:
        if not os.path.exists(file_path):
            await result_command_change(f"Файл не найден: {file_path}", Color.RED)
            return

        lines = []
        with open(file_path, "r") as reader:
            i = 1
            for line in reader:
                if i == delete_line:
                    await result_command_change(f"Line removed: {line}", Color.GRAY)
                else:
                    lines.append(line)
                i += 1

        with open(file_path, "w") as writer:
            for line in lines:
                writer.write(line)
    except IOError as e:
        await result_command_change(f"Ошибка  (ID:f10) {e}", Color.RED)


async def file_was_filler(folder, file_list):
    try:
        for root, _, files in os.walk(folder):
            for file in files:
                if not os.path.isdir(file):
                    file_list.append(os.path.join(root, file))
        return file_list
    except IOError as e:
        await result_command_change(f"Ошибка (ID:f11)  {e}", Color.RED)


async def get_link_to_file(zip_name, ctx):
    try:
        process = await asyncio.create_subprocess_shell(
            f"curl -T \"{zip_name}\" https://pixeldrain.com/api/file/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )

        stdout, stderr = await process.communicate()

        for line in stdout.decode().split('\n'):
            if line.strip():
                print(line)
                # {"id":"123"}
                if "id" in line:
                    line = line[line.find(":") + 2:]
                    line = line[:line.find("\"")]
                    return "https://pixeldrain.com/u/" + line
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка выполнения команды (ID:z1): {e}")
    except Exception as e:
        await ctx.send(f"Произошла неизвестная ошибка (ID:z2): {e}")


async def play_audio_process(ctx):
    await asyncio.sleep(0.1)
    try:
        await set_get_config_all('Values', "queue", "True")
        while True:
            with open("caversAI/queue.txt") as reader:
                line = reader.readline()
                if not line is None and not line.replace(" ", "") == "":
                    time = await extract_number_after_keyword(line, "-time")
                    output = line[line.find("-output") + 8:]
                    output = output[:output.find(" ")]
                    stop_milliseconds = await extract_number_after_keyword(line, "-start")
                    audio_path = line[:line.find(" -time")]

                    if not output == "None":
                        await ctx.send("===Файлы " + os.path.basename(audio_path)[:-4] + "===")

                        output = output.replace(" ", "")
                        from discord_bot import send_file
                        # конечный файл
                        if output == "file":
                            await send_file(ctx, audio_path)
                        # все файлы
                        elif output == "all_files":
                            for filename in os.listdir(os.path.dirname(audio_path)):
                                file_path = os.path.join(os.path.dirname(audio_path), filename)
                                await send_file(ctx, file_path, delete_file=True)
                        # zip файл по ссылке
                        elif output == "link":
                            zip_name = os.path.dirname(audio_path) + f"/all_files.zip"
                            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for filename in os.listdir(os.path.dirname(audio_path)):
                                    file_path = os.path.join(os.path.dirname(audio_path), filename)
                                    if ".zip" in file_path:
                                        continue
                                    zipf.write(file_path, os.path.basename(file_path))
                            link = await get_link_to_file(zip_name, ctx)
                            await ctx.send(f"Ссылка на скачку:{link}")
                            # link = await get_link_to_file(os.path.dirname(audio_path) + "/combined.m4a", ctx)
                            # await ctx.send(f"Ссылка на скачку архива:{link}")
                    else:
                        await ctx.send("Играет " + os.path.basename(audio_path)[:-4])
                    await result_command_change("Играет " + os.path.basename(audio_path)[:-4], Color.GREEN)
                    await playSoundFile(audio_path, time, stop_milliseconds, ctx)
                    await remove_line_from_txt("caversAI/queue.txt", 1)
                else:
                    config.read('config.ini')
                    continue_process = config.getboolean('Values', 'queue')
                    await asyncio.sleep(0.5)
                    if not continue_process:
                        await result_command_change(f"file_have_links - False", Color.CYAN)
                        break
    except (IOError, KeyboardInterrupt) as e:
        await result_command_change("Произошла ошибка (ID:f12):" + str(e), Color.RED)
        await write_in_discord(ctx, "Произошла ошибка (ID:f12):" + str(e))


async def wait_for_file(file_name, max_attempts, delay):
    max_attempts += 1
    attempt = 0
    file = os.path.join(os.getcwd(), file_name)
    while attempt < max_attempts and not os.path.exists(file):
        await asyncio.sleep(delay)
        if attempt % 50 == 49:
            print(f"Файла нет. Попытка: {attempt + 1}")
        attempt += 1
    if attempt == max_attempts:
        return False
    return True


async def console_command_runner(command, ctx):
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()

        for line in stdout.decode().split('\n'):
            if "File is larger than max-filesize" in line:
                await text_to_speech("Видео должно быть меньше пяти минут", False, ctx)
                return False
            if "because it has not reached minimum view count" in line:
                index1 = line.index("(")
                index2 = line.index("/")
                await text_to_speech(
                    f"На видео должно быть минимум пятьдесят тысяч просмотров, на этом видео их {line[index1 + 1:index2]}",
                    False, ctx)
                return False
            process.kill()

        error_got = False
        for line in stderr.decode().split('\n'):
            print(line)
            if "This video may be inappropriate for some users" in line:
                await text_to_speech("Видео не должно быть с возрастными ограничениями", False, ctx)
                return False
            if "Falling back on generic information extractor" in line:
                await text_to_speech("Не получилось получить информацию о видео", False, ctx)
                return False
            if "Unsupported URL" in line:
                await text_to_speech("Неправильная ссылка", False, ctx)
                return False
            error_got = True

        if error_got:
            await text_to_speech("Видео не скачалось по неизвестной причине", False, ctx)
            return False
        return True
    except (subprocess.CalledProcessError, IOError, Exception) as e:
        await result_command_change("Произошла ошибка (ID:f13):" + str(e), Color.RED)

async def speed_up_audio(input_file, speed_factor):
    audio = AudioSegment.from_file(input_file)
    sped_up_audio = audio.speedup(playback_speed=speed_factor)
    sped_up_audio.export(input_file, format="mp3")


async def text_to_speech(tts, write_in_memory, ctx, ai_dictionary=None):
    currentpitch = int(await set_get_config_all("Default", "currentaipitch", None))
    if tts is None or tts.replace("\n", "").replace(" ", "") == "":
        await result_command_change(f"Пустой текст \"{tts}\"", Color.RED)
        return
    await result_command_change(tts, Color.GRAY)
    # убираем маты
    tts = await replace_mat_in_sentence(tts)

    # убираем текст до коментария
    if "||" in tts:
        tts = re.sub(r'\|\|.*?\|\|', '', tts)

    # меняем голос на текущий
    if ai_dictionary is None:
        global currentAIname
        ai_dictionary = currentAIname
        print("TTS_voice:", currentAIname)
    # записываем в память
    if write_in_memory:
        try:
            with open(f"texts/memories/{ai_dictionary}.txt", 'a') as writer2:
                tts_no_n = tts.replace("\n", " ")
                writer2.write(f"GPT: {tts_no_n}\n")
        except IOError as e:
            await result_command_change("Произошла ошибка (ID:f14):" + str(e), Color.RED)
        lines_number = 0
        with open(f"texts/memories/{ai_dictionary}.txt", 'r') as reader:
            lines = reader.readlines()
            lines_number = len(lines)
        while lines_number > 5:
            lines_number -= 1
            try:
                with open(f"texts/memories/{ai_dictionary}.txt", 'r') as reader:
                    lines = reader.readlines()
                lines = lines[2:]
                with open(f"texts/memories/{ai_dictionary}.txt", 'w') as writer:
                    writer.writelines(lines)
            except IOError as e:
                await result_command_change(f"Ошибка при выполнении команды (ID:f51): {e}", Color.RED)

    if not ctx.voice_client:
        await result_command_change("skip tts", Color.CYAN)
        return
    file_name = "1.mp3"

    if os.path.exists(file_name):
        os.remove(file_name)

    from discord_bot import text_to_speech_file
    pitch = await text_to_speech_file(tts, currentpitch, file_name)
    # если голос не выставлен
    if ai_dictionary == "None":
        await playSoundFile(file_name, -1, 0, ctx)
        await result_command_change(f"tts(No RVC)", Color.CYAN)
        return

    # используем RVC
    try:
        command = [
            "python",
            "only_voice_change_cuda0.py",
            "-i", f"\"{file_name}\"",
            "-o", "2.mp3",
            "-dir", str(ai_dictionary),
            "-p", f"{pitch}",
            "-ir", "0.5",
            "-fr", "3",
            "-rms", "0.3",
            "-pro", "0.15"
        ]
        print("run RVC, AIName:", ai_dictionary)
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        await result_command_change(f"Ошибка при выполнении команды (ID:f17): {e}", Color.RED)
        await playSoundFile("1.mp3", -1, 0, ctx)
        return
    await result_command_change("done RVC", Color.GREEN)
    # применение ускорения
    if await set_get_config_all("Sound", "change_speed", None) == "True":
        with open(os.path.join(f"rvc_models/{ai_dictionary}/speed.txt"), "r") as reader:
            speed = float(reader.read())
        await speed_up_audio("2.mp3", speed)

    # "2.mp3"
    await playSoundFile("2.mp3", -1, 0, ctx)
    await result_command_change(f"tts: {tts}", Color.GRAY)


async def gtts(tts, language, output_file):
    print("GTTS_fun", language, output_file)
    try:
        voiceFile = gTTS(tts, lang=language)
        # Сохранение в файл
        voiceFile.save(output_file)
    except Exception as e:
        await result_command_change(f"Ошибка при синтезе речи: {e}", Color.YELLOW)


async def remove_unavaible_voice_token():
    tokens = (await set_get_config_all("voice", "avaible_tokens")).split(";")
    avaible_tokens = ""
    if len(tokens) == 1:
        await set_get_config_all("voice", "avaible_tokens", "None")
        await result_command_change("==БОЛЬШЕ НЕТ ТОКЕНОВ ДЛЯ СИНТЕЗА ГОЛОСА==", Color.YELLOW)
        return
    skip_first = True
    for token in tokens:
        if skip_first:
            skip_first = False
            continue
        avaible_tokens += token
    await set_get_config_all("voice", "avaible_tokens", avaible_tokens)


async def setModelWithLanguage(language, model_type):
    if model_type == "tts":
        if language == "russian":
            return "Irina"
        elif language == "english":
            return "Alan"
        elif language == "ukrainian":
            return "Anatol"
        elif language == "tatar":
            return "Talgat"
    elif model_type == "stt":
        if language in ["russian", "tatar"]:
            return "modelRU"
        elif language == "english":
            return "modelEN"
        elif language == "ukrainian":
            return "modelUK"
    return None


async def playSoundFile(audio_file_path, duration, start_seconds, ctx):
    from discord_bot import playSoundFileDiscord
    try:
        if not ctx.voice_client:
            print("Skip play")
            return

        if not os.path.exists(audio_file_path):
            await result_command_change(f"Файл {audio_file_path} недоступен", Color.RED)
            return

        # Проверяем, чтобы ничего не играло
        # перенесено

        if duration <= 0:
            duration = len(AudioSegment.from_file(audio_file_path)) / 1000

        await playSoundFileDiscord(ctx, audio_file_path, duration, start_seconds)
        print("Аудио закончилось")
    except TimeoutError:
        pass
    except Exception as e:
        print("Ошибка проигрывания файла: ", e)


async def fileFind(sentence, ctx):
    global files_found

    words = sentence.split()
    groupSize = 3

    for i in range(len(words) - groupSize + 1):
        if files_found == 0:
            group = " ".join(words[i:i + groupSize])
            directoryPath = "temp"
            await find_in_files(group, directoryPath, ctx)

    if files_found == 0:
        await text_to_speech("не найдено", False, ctx)


async def find_in_files(targetGroup, directoryPath, ctx):
    global files_found, current_file

    for filename in os.listdir(directoryPath):
        if filename.endswith(".wav"):
            try:
                with open(os.path.join(directoryPath, filename)) as file:
                    content = file.read()
                    content = preprocess_text(content)

                    if targetGroup in content:
                        if files_found == 0:
                            current_file = filename[:-4]
                            await text_to_speech(f"Похоже, что это {filename[:-4]}", False, ctx)
                        files_found += 1
            except Exception as e:
                print("Ошибка при чтении файла:", e)


async def preprocess_text(text):
    processed_text = text.replace("\n", " ")
    processed_text = ''.join(char for char in processed_text if char.isalpha() or char.isspace()).lower()
    processed_text = ' '.join(processed_text.split())
    processed_text = processed_text.replace("ё", "е")
    return processed_text


async def extract_number_after_keyword(input, keyword):
    index = input.find(keyword)
    if index != -1:
        remaining_str = input[index + len(keyword) + 1:]
        if " " in remaining_str:
            remaining_str = remaining_str[:remaining_str.find(" ")]
        if remaining_str:
            if remaining_str[0] == '-':
                numberStr = '-' + ''.join(char for char in remaining_str[1:] if char.isdigit())
            else:
                numberStr = ''.join(char for char in remaining_str if char.isdigit())
            if numberStr:
                # await result_command_change(f"Extract: {keyword}, Number:{numberStr}", Color.GRAY)
                return int(numberStr)
    return -1


async def extract_double_after_keyword(input, keyword):
    index = input.find(keyword)

    if index != -1:
        remaining_str = input[index + len(keyword) + 1:]
        if " " in remaining_str:
            remaining_str = remaining_str[:remaining_str.find(" ")]
        numberStr = ''.join(char for char in remaining_str if char.isdigit() or char == '.')

        try:
            if numberStr:
                return float(numberStr.replace(',', '.'))
        except ValueError as e:
            await result_command_change("Произошла ошибка (ID:f18):" + str(e), Color.RED)

    return -1


files_found = 0
current_file = "не найдено"


async def remove_before_stop(input_str, target_word):
    index = input_str.find(target_word)

    if index != -1:
        return input_str[index + len(target_word):]

    return input_str
