import asyncio
import multiprocessing
import sys
from translate import Translator
import subprocess
import re
import time
import os

from elevenlabs import generate, play, save
from discord_bot import config
from discord_bot import write_in_discord
from use_free_cuda import use_cuda, stop_use_cuda, check_cuda, wait_for_cuda_async, stop_use_cuda_async, use_cuda_async


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
prompt_length = 1
admin = True
all_admin = False
video_length = 5
currentAIname = ""
currentAIinfo = ""
currentAIpitch = 0
robot_names = []


async def set_config(key, value):
    config.read('config.ini')
    config.set('Default', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def set_get_config_all(section, key, value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.get(section, key)
    config.set(section, key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


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
    global currentAIname
    currentAIname = config.get('Default', 'currentainame')
    global currentAIinfo
    currentAIinfo = config.get('Default', 'currentaiinfo')
    global currentAIpitch
    currentAIpitch = config.getint('Default', 'currentaipitch')
    global robot_names
    robot_names = ["robot", "robots", "робот", "нейросеть", "hello", "роботы", "ропот"]

    print("RowInput:", spokenText)
    temp_spokenText = spokenText

    while "стоп" in temp_spokenText:
        temp_spokenText = await remove_before_stop(temp_spokenText, "стоп")

    while "Стоп" in temp_spokenText:
        temp_spokenText = await remove_before_stop(temp_spokenText, "Стоп")
    if await is_robot_name(temp_spokenText, ctx):
        await result_command_change("Обработка...", Color.BLACK)
        try:
            print("check... Голосовая команда")
            if await voice_commands(temp_spokenText.lower(), ctx):
                print("Голосовая команда")
                return
        except Exception as ex:
            raise ex

        try:
            # file_path = "texts/memories/" + str(currentAIname) + ".txt"
            # if not os.path.exists(file_path):
            #     print("File doesn't exist, creating a new one.")
            #     with open(file_path, "w") as create_file:
            #         create_file.write(
            #             await utf_code("Человек: Привет!\n" + currentAIname + ": Привет, как я могу помочь?\n"))
            # Open the file
            # with open(file_path, "r") as file:
            #     file_content = file.read()
            # prompt = f"Напиши ответ человеку, он говорит:\""
            prompt = f"Представь, что тебя зовут {currentAIname}. {currentAIinfo}. Тебе пишут: {temp_spokenText}. Ответ:"
            # prompt = f"Представь, что тебя зовут {currentAIname}. {currentAIinfo}." \
            #          f"Тебе нужно вести диалог. Ты не говоришь, что какую-либо выполняешь роль (Например: " \
            #          f"я не могу выполнить такие действия, так как это нарушает мою роль). " \
            #          f"Отвечай как можно короче. " \
            #          f"У тебя ({currentAIname}) есть воспоминания:\"{file_content}\". " \
            #          f"Напиши ответ человеку, он говорит:\""
            # prompt += temp_spokenText + "\". Ответ: "
        except Exception as ex:
            raise ex

        try:
            await chatgpt_get_result(True, prompt, ctx, writeAnswer)
        except Exception as ex:
            raise ex


async def is_robot_name(text, ctx):
    if text.startswith(currentAIname.lower()[:-1]):
        if text == currentAIname:
            await text_to_speech("да?", False, ctx)
            return False
        return True
    global robot_names
    for name in robot_names:
        if text.startswith(name):
            print("имя робота найдено!")
            return True
    return False


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
    "апездал", "апездошенная", "блядь", "блять", "бля", "блядство", "выебон", "выебать", "вхуюжить", "гомосек", "долбоёб",
    "ебло", "еблище", "ебать", "ебическая", "ебунок", "еблан", "ёбнуть", "ёболызнуть", "ебош", "заебал",
    "заебатый", "злаебучий", "заёб", "хуй", "колдоебина", "манда", "мандовошка", "мокрощелка", "наебка",
    "наебал", "наебаловка", "напиздеть", "отъебись", "охуеть", "отхуевертить", "опизденеть", "охуевший",
    "отебукать", "пизда", "пидарас", "пиздатый", "пиздец", "пизданутый", "поебать", "поебустика", "проебать",
    "подзалупный", "пизденыш", "припиздак", "разъебать", "распиздяй", "разъебанный", "сука", "трахать",
    "уебок", "уебать", "угондошить", "уебан", "хитровыебанный", "хуйня", "хуета", "хуево", "хуесос",
    "хуеть", "хуевертить", "хуеглот", "хуистика", "членосос", "членоплет", "шлюха", "fuck", "тест_мат",
    "порно", "секс", "черножопая",  "нахуй"
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


async def chatgpt_get_result(write_in_memory, prompt, ctx, writeAnswer):
    config.read('config.ini')
    gpt_loaded = config.getboolean('gpt', 'gpt')
    print("DEV_TEMP_gpt_loaded:", gpt_loaded)
    if not gpt_loaded:
        await write_in_discord(ctx, "модель чат-бота не загрузилась, подождите пару минут")
        return
    print('generating answer')
    await set_get_config_all("gpt", "gpt_prompt", prompt)
    result = "None"
    while result == "None":
        result = await set_get_config_all("gpt", "gpt_result")
        if result.endswith('$$'):
            index_answer = result.index("Ответ:")
            if not index_answer == -1:
                result = result[index_answer + 6:-2]
            break
        await asyncio.sleep(0.05)
    await set_get_config_all("gpt", "gpt_result", "None")
    if not language == "russian":
        translator = Translator(from_lang="ru", to_lang=language[:2].lower())
        result = translator.translate(result)
    if writeAnswer:
        await write_in_discord(ctx, result)
    await text_to_speech(result, write_in_memory, ctx)


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

    print("Input:", sentence)

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
            print(f"Завершение кода по протоколу через {seconds_delay}")
            await asyncio.sleep(seconds_delay + 0.01)
            # await exit_from_voice(ctx)
            await write_in_discord(ctx, "*выключение*")
            from discord_bot import disconnect
            await disconnect(ctx)
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
            await chatgpt_get_result(False, sentence[sentence.index("gpt") + 3:], ctx, True)
        except Exception as e:
            raise RuntimeError(e)
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
            print("Протокол", protocol_number)
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
                    create_file.write(
                        "Человек: Привет!\n" + currentAIname + ": Привет, как я могу помочь?\n")
                await text_to_speech("отчищена память", False, ctx)
            except Exception as e:
                print("Error:", e)
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
            await textInDiscord(spoken_text_temp, ctx)
            return True
        # AICoverGen
        elif protocol_number == 13:
            if not admin:
                await text_to_speech("нужны права администратора", False, ctx)
                return True
            await createAICaver(ctx)
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
        await setAIvoice(sentence, True, ctx)
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


async def setAIvoice(name, ttsNeed, ctx):
    global currentAIname, currentAIinfo, currentAIpitch
    if os.path.exists(f"rvc_models/{name}"):
        with open(os.path.join(f"rvc_models/{name}/info.txt")) as file:
            await set_config(currentAIinfo, file.read())
        await set_config("currentainame", name)
        with open(os.path.join(f"rvc_models/{name}/gender.txt")) as file:
            if file.read().lower() == "female":
                await set_config("currentaipitch", 0)
            else:
                await set_config("currentaipitch", -1)
    else:
        await text_to_speech("голос не найден", False, ctx)


async def textInDiscord(message, ctx):
    while "пользовател" in message:
        message = re.sub(r'\s+', ' ', message)
        if message.endswith(' '):
            message = message[:-1]
        user = await getUserName(message, "пользовател")
        message = await replaceWords(message, "пользовател", user)
        message = await removePunctuation(message, 3)
    print("writing " + message)
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
        print("DEV_TEMP_SPOKEN_TEXT:", spokenText)
        lines = message.split("\n")
        if not os.path.exists("caversAI/audio_links.txt"):
            with open("caversAI/audio_links.txt", "w"):
                pass
        print("temp1")
        with open("caversAI/audio_links.txt", "a") as writer:
            for line in lines:
                writer.write(line + "\n")
        print("temp2")
        config.read('config.ini')
        continue_process = config.getboolean('Values', 'queue')
        if not continue_process:
            print("temp3")
            await use_cuda_async(0)
            await use_cuda_async(1)
            await write_in_discord(ctx, "Начинаю обработку аудио")
            pool = multiprocessing.Pool(processes=1)
            pool.apply_async(prepare_audio_process_cuda, (ctx,))
            pool.close()
            pool.join()
            print("ready audios")
            # освобождаем видеокарты
            await stop_use_cuda_async(0)
            await stop_use_cuda_async(1)
        else:
            print("temp4")
            # добавляем те, которые сейчас обрабатываются
            queue_position = check_cuda()
            with open("caversAI/audio_links.txt", "r") as reader:
                lines = reader.readlines()
                queue_position += len(lines)
            with open("caversAI/queue.txt", "r") as reader:
                lines = reader.readlines()
                queue_position += len(lines)
            await write_in_discord(ctx, "Аудио добавлено в очередь. Место в очереди: " + str(queue_position))
    except Exception as e:
        print(f"Произошла ошибка: {e}")


async def getCaverPrms(line, ctx):
    global currentAIname, currentAIinfo
    # SONG_INPUT
    url = "."
    if "-url" in line:
        if "https" in line:
            url = line[line.index("https"):]
            if " " in url:
                url = url[:url.index(" ")]

    # RVC_DIRNAME
    voice = currentAIname
    if "-voice" in line:
        voice = line[line.index("-voice") + 7:]
        voice = voice[0, voice.index(" "):]
        currentAInameWas = currentAIname
        await setAIvoice(voice, False, ctx)
        voice = currentAIname
        await setAIvoice(currentAInameWas, False, ctx)

    # PITCH_CHANGE
    pitch = 0
    if "-pitch" in line:
        pitch = await extract_number_after_keyword(line, "-pitch")
        if pitch < -2 or pitch > 2:
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

    outputFormat = "mp3"

    return f"python src/main.py -i {url} -dir modelsRVC/{voice} -p {pitch} -ir {indexrate} -rms {loudness} -mv {mainVocal} -bv {backVocal} -iv {music} -rsize {roomsize} -rwet {wetness} -rdry {dryness} -start {start} -time {time} -oformat {outputFormat}"


# async def defaultRVCParams(filePath, pitch):
#     return f"python ../AICoverGen/src/main.py -i {filePath} -dir modelsRVC/{currentAIname} -p 0 -ir {pitch} -rms 0.3 -mv 0 -bv -20 -iv -20 -rsize 0.2 -rwet 0.1 -rdry 0.95 -start 0 -time -1 -oformat wav"

def prepare_audio_process_cuda(ctx):
    while True:
        try:
            with open("caversAI/audio_links.txt") as reader:
                line = reader.readline()
                if not line == "" and not line is None:
                    if "https://youtu.be/" not in line and "https://www.youtube.com/" not in line:
                        asyncio.run(text_to_speech("Видео должно быть с ютуба", False, ctx))
                        asyncio.run(result_command_change("Ссылка не с YT", Color.RED))
                        asyncio.run(remove_line_from_txt("caversAI/audio_links.txt", 1))
                        continue

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

                    params = asyncio.run(getCaverPrms(line, ctx))
                    asyncio.run(remove_line_from_txt("caversAI/audio_links.txt", 1))
                    print("запуск AICoverGen")
                    print(params)
                    asyncio.run(console_command_runner(params, ctx))
                    time.sleep(0.05)
                else:
                    print("Больше нет ссылок")
                    asyncio.run(set_get_config_all('Values', "queue", "False"))
                    break
        except (IOError, KeyboardInterrupt):
            pass


async def remove_line_from_txt(file_path, delete_line):
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        lines = []
        with open(file_path, "r") as reader:
            i = 1
            for line in reader:
                if i == delete_line:
                    print(f"Line removed: {line}")
                else:
                    lines.append(line)
                i += 1

        with open(file_path, "w") as writer:
            for line in lines:
                writer.write(line)
    except IOError as e:
        print(e)


async def file_was_filler(folder, file_list):
    try:
        for root, _, files in os.walk(folder):
            for file in files:
                if not os.path.isdir(file):
                    file_list.append(os.path.join(root, file))
        return file_list
    except IOError as e:
        print(e)


def play_audio_process(ctx):
    try:
        asyncio.run(set_get_config_all('Values', "queue", "True"))
        while True:
            with open("caversAI/queue.txt") as reader:
                line = reader.readline()
                if not line is None:
                    print("Playing: " + line)
                    params = asyncio.run(getCaverPrms(line, ctx))
                    time = asyncio.run(extract_number_after_keyword(params, "-time"))
                    stop_milliseconds = asyncio.run(extract_number_after_keyword(params, "-start"))
                    audio_path = line.split()[0]

                    asyncio.run(result_command_change("Играет " + os.path.basename(audio_path)[:-4], Color.GREEN))
                    asyncio.run(playSoundFile(audio_path, time, stop_milliseconds, ctx))
                    asyncio.run(remove_line_from_txt("caversAI/queue.txt", 1))
                else:
                    config.read('config.ini')
                    continue_process = config.getboolean('Values', 'queue')
                    if not continue_process:
                        print("file_have_links - False")
                        break
    except (IOError, KeyboardInterrupt):
        pass


async def wait_for_file(file_name, max_attempts, delay):
    max_attempts += 1
    attempt = 0
    file = os.path.join(os.getcwd(), file_name)
    while attempt < max_attempts and not os.path.exists(file):
        time.sleep(delay)
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
    except (subprocess.CalledProcessError, IOError, Exception):
        pass


async def text_to_speech(tts, write_in_memory, ctx, ai_dictionary=None):
    await result_command_change(tts, Color.GRAY)
    tts = await replace_mat_in_sentence(tts)
    if ai_dictionary is None:
        global currentAIname
        ai_dictionary = currentAIname
        print(currentAIname)
    if write_in_memory:
        try:
            with open(f"texts/memories/{ai_dictionary}.txt", 'a') as writer2:
                writer2.write(f"{ai_dictionary}: {tts}\n")
        except IOError as ex:
            raise RuntimeError(ex)

        while os.path.getsize(f"texts/memories/{ai_dictionary}.txt") > 500:
            try:
                with open(f"texts/memories/{ai_dictionary}.txt", 'r') as reader:
                    lines = reader.readlines()
                lines = lines[2:]
                with open(f"texts/memories/{ai_dictionary}.txt", 'w') as writer:
                    writer.writelines(lines)
            except IOError as e:
                print(e)
    if not ctx.voice_client:
        print(f"skip_tts: {tts}")
        return
    file_name = "1.mp3"

    if os.path.exists(file_name):
        os.remove(file_name)
    language = await set_get_config_all("Default", "language") 
    if len(tts) > 200 or await set_get_config_all("voice", "avaible_tokens") == "None":
        print("gtts1")
        await gtts(tts, language[:2], file_name)
        return
    try:
        # голос TTS в зависимости от пола
        if currentAIpitch == 0:
            voice = "Arnold"
        else:
            voice = "Bella"
        audio = generate(
            text=tts,
            model='eleven_multilingual_v2',
            voice=voice
        )

        save(audio, file_name)
    except Exception as e:
        print(f"Ошибка при выполнении команды: {e}")
        await remove_unavaible_voice_token()
        await text_to_speech(tts, False, ctx, ai_dictionary=ai_dictionary)
        return
        #gtts(tts, language[:2], file_name)
    # если голос не выставлен
    if ai_dictionary == "None":
        await playSoundFile(file_name, -1, 0, ctx)
        print(f"tts(No RVC): {tts}")
        return

    # используем RVC
    successful = True
    try:
        command = [
            "python",
            "src/only_voice_change.py",
            "-i", file_name,
            "-o", "2.mp3",
            "-dir", str(ai_dictionary),
            "-p", "0",
            "-ir", "0.5",
            "-fr", "3",
            "-rms", "0.3",
            "-pro", "0.15"
        ]
        print("run RVC, AIName:", ai_dictionary)
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
        await playSoundFile("1.mp3", -1, 0, ctx)
        successful = False
        return
    if successful:
        print("done RVC")
        await playSoundFile("2.mp3", -1, 0, ctx)
        print(f"tts: {tts}")


async def gtts(tts, language, output_file):
    from gtts import gTTS
    
    # на вход идёт всегда русский текст, так что переводим его
    try:
        voiceFile = gTTS(tts, lang=language)
        # Сохранение в файл
        voiceFile.save(output_file)
    except Exception as e:
        print(f"Произошла ошибка при синтезе речи: {str(e)}")


async def remove_unavaible_voice_token():
    tokens = (await set_get_config_all("voice", "avaible_tokens")).split(";")
    avaible_tokens = ""
    if len(tokens):
        await set_get_config_all("voice", "avaible_tokens", "None")
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
    from pydub import AudioSegment
    from discord_bot import playSoundFileDiscord

    if not await wait_for_file(audio_file_path, 500, 100):
        print("Файл недоступен")
        return

    # Проверяем, чтобы ничего не играло
    # перенесено

    if duration <= 0:
        duration = len(AudioSegment.from_file(audio_file_path)) / 1000

    await playSoundFileDiscord(ctx, audio_file_path, duration, start_seconds)
    print("Аудио закончилось")


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
    input = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in input)
    index = input.find(keyword)

    if index != -1:
        start = index + len(keyword) + 1
        end = input.find(" ", start) if " " in input[start:] else len(input)
        numberStr = ''.join(char for char in input[start:end] if char.isdigit())

        if numberStr:
            return int(numberStr)

    return -1


async def extract_double_after_keyword(input, keyword):
    input = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in input)
    index = input.find(keyword)

    if index != -1:
        start = index + len(keyword) + 1
        end = input.find(" ", start) if " " in input[start:] else len(input)
        numberStr = ''.join(char for char in input[start:end] if char.isdigit() or char == '.')

        try:
            if numberStr:
                return float(numberStr.replace(',', '.'))
        except ValueError:
            pass

    return -1


files_found = 0
current_file = "не найдено"


async def remove_before_stop(input_str, target_word):
    index = input_str.find(target_word)

    if index != -1:
        return input_str[index + len(target_word):]

    return input_str
