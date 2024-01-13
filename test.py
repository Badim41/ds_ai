import asyncio
import nextcord
import os
import random
import re
import subprocess
import sys
import traceback
from nextcord import Interaction, SlashOption, Attachment
from nextcord.ext import commands
from pydub import AudioSegment
from pytube import Playlist

import json

from discord import SlashCommandOptionType
from set_get_config import set_get_config_all

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)


@bot.event
async def on_ready():
    print('Status: online')
    await bot.change_presence(activity=nextcord.Activity(
        type=nextcord.ActivityType.listening, name='AI-covers'))
    id = await set_get_config_all("Default", "reload")
    print("ID:", id)
    if not id == "True":
        user = await bot.fetch_user(int(id))
        await user.send("Перезагружен!")


@bot.slash_command(name="config", description='изменить конфиг (лучше не трогать, если не знаешь!)')
async def config_command(
        interaction: Interaction,
        section: str = SlashOption(
            name="section",
            description="секция",
            required=True
        ),
        key: str = SlashOption(
            name="key",
            description="ключ",
            required=True
        ),
        value: str = SlashOption(
            name="value",
            description="значение",
            required=False,
            default=None
        )
):
    try:

        owner_id = await set_get_config_all("Default", "owner_id")
        if not interaction.user.id == int(owner_id):
            await interaction.user.send("Доступ запрещён")
            return
        result = await set_get_config_all(section, key, value)
        if value is None:
            await interaction.response.send_message(result)
        else:
            await interaction.response.send_message(section + " " + key + " " + value)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await interaction.response.send_message(
            f"Ошибка при изменении конфига (с параметрами{section},{key},{value}): {e}")


@bot.slash_command(name="join", description='присоединиться к голосовому каналу')
async def join(interaction: Interaction):
    try:
        await interaction.response.defer()

        # уже в войс-чате
        if interaction.guild.voice_client is not None:
            await interaction.response.send_message("Бот уже находится в голосовом канале.")
            return

        voice = interaction.user.voice
        if not voice:
            await interaction.response.send_message("error: not in voice")
            return

        voice_channel = voice.channel

        await voice_channel.connect()
        await interaction.response.send_message("Присоединяюсь")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await interaction.response.send_message(f"Ошибка при присоединении: {e}")


@bot.slash_command(name="disconnect", description='выйти из войс-чата')
async def disconnect(interaction: Interaction):
    try:

        voice = interaction.guild.voice_client
        if voice:
            await voice.disconnect(force=True)
            await interaction.response.send_message("выхожу")
        else:
            await interaction.response.send_message("Я не в войсе")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await interaction.response.send_message(f"Ошибка при выходе из войс-чата: {e}")


async def get_links_from_playlist(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        video_links = playlist.video_urls
        video_links = str(video_links).replace("'", "").replace("[", "").replace("]", "").replace(" ", "").replace(",",
                                                                                                                   ";")
        return video_links
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        print(f"Произошла ошибка при извлечении плейлиста: {e}")
        return []


@bot.slash_command(name="ai_cover", description='Заставить бота озвучить видео/спеть песню')
async def ai_cover(
        ctx: Interaction,
        url: str = SlashOption(
            name="url",
            description="Ссылка на видео",
            required=False,
            default=None
        ),
        voice: str = SlashOption(
            name="voice",
            description="Голос для видео",
            required=False,
            default=None
        ),
        gender: str = SlashOption(
            name="gender",
            description="Кто говорит/поёт в видео? (или указать pitch)",
            required=False,
            choices=['мужчина', 'женщина'],
            default=None
        ),
        pitch: int = SlashOption(
            name="pitch",
            description="Какую использовать тональность (от -24 до 24) (или указать gender)",
            required=False,
            default=0,
            min_value=-24,
            max_value=24
        ),
        time: int = SlashOption(
            name="time",
            description="Ограничить длительность воспроизведения (в секундах)",
            required=False,
            default=-1,
            min_value=-1
        ),
        indexrate: float = SlashOption(
            name="indexrate",
            description="Индекс голоса (от 0 до 1)",
            required=False,
            default=0.5,
            min_value=0,
            max_value=1
        ),
        loudness: float = SlashOption(
            name="loudness",
            description="Громкость шума (от 0 до 1)",
            required=False,
            default=0.4,
            min_value=0,
            max_value=1
        ),
        filter_radius: int = SlashOption(
            name="filter_radius",
            description="Насколько далеко от каждой точки в данных будут учитываться значения... (от 1 до 7)",
            required=False,
            default=3,
            min_value=0,
            max_value=7
        ),
        main_vocal: int = SlashOption(
            name="main_vocal",
            description="Громкость основного вокала (от -50 до 0)",
            required=False,
            default=0,
            min_value=-50,
            max_value=0
        ),
        back_vocal: int = SlashOption(
            name="back_vocal",
            description="Громкость бэквокала (от -50 до 0)",
            required=False,
            default=0,
            min_value=-50,
            max_value=0
        ),
        music: int = SlashOption(
            name="music",
            description="Громкость музыки (от -50 до 0)",
            required=False,
            default=0,
            min_value=-50,
            max_value=0
        ),
        roomsize: float = SlashOption(
            name="roomsize",
            description="Размер помещения (от 0 до 1)",
            required=False,
            default=0.2,
            min_value=0,
            max_value=1
        ),
        wetness: float = SlashOption(
            name="wetness",
            description="Влажность (от 0 до 1)",
            required=False,
            default=0.2,
            min_value=0,
            max_value=1
        ),
        dryness: float = SlashOption(
            name="dryness",
            description="Сухость (от 0 до 1)",
            required=False,
            default=0.8,
            min_value=0,
            max_value=1
        ),
        palgo: str = SlashOption(
            name="palgo",
            description="Алгоритм. Rmvpe - лучший вариант, mangio-crepe - более мягкий вокал",
            required=False,
            choices=['rmvpe', 'mangio-crepe'],
            default="rmvpe"
        ),
        hop: int = SlashOption(
            name="hop",
            description="Как часто проверяет изменения тона в mango-crepe",
            required=False,
            default=128,
            min_value=64,
            max_value=1280
        ),
        start: int = SlashOption(
            name="start",
            description="Начать воспроизводить с (в секундах). -1 для продолжения",
            required=False,
            default=0,
            min_value=-2
        ),
        output: str = SlashOption(
            name="output",
            description="Отправить результат",
            choices=["ссылка на все файлы", "только результат (1 файл)", "все файлы", "не отправлять"],
            required=False,
            default="только результат (1 файл)"
        ),
        only_voice_change: bool = SlashOption(
            name="only_voice_change",
            description="Не извлекать инструментал и бэквокал, изменить голос. Не поддерживаются ссылки",
            required=False,
            default=False
        ),
        audio_path: Attachment = SlashOption(
            name="audio_path",
            description="Аудиофайл",
            required=False,
            default=None
        )
):
    param_string = None
    # ["link", "file", "all_files", "None"], ["ссылка на все файлы", "только результат (1 файл)", "все файлы", "не отправлять"]
    output = output.replace("ссылка на все файлы", "link").replace("только результат (1 файл)", "file").replace(
        "все файлы", "all_files").replace("не отправлять", "None")
    try:

        await ctx.response.send_message('Выполнение...')
        params = []
        if voice is None:
            voice = await set_get_config_all("Default", "currentAIname")
        if voice:
            params.append(f"-voice {voice}")
        # если мужчина-мужчина, женщина-женщина, pitch не меняем
        pitch_int = pitch
        # если женщина, а AI мужчина = -12,
        if gender == 'женщина':
            if await set_get_config_all("Default", "currentaipitch") == "0":
                pitch_int = -12
        # если мужчина, а AI женщина = 12,
        elif gender == 'мужчина':
            if not await set_get_config_all("Default", "currentaipitch") == "0":
                pitch_int = 12
        params.append(f"-pitch {pitch_int}")
        if time is None:
            params.append(f"-time -1")
        else:
            params.append(f"-time {time}")
        if palgo != "rmvpe":
            params.append(f"-palgo {palgo}")
        if hop != 128:
            params.append(f"-hop {hop}")
        if indexrate != 0.5:
            params.append(f"-indexrate {indexrate}")
        if loudness != 0.2:
            params.append(f"-loudness {loudness}")
        if filter_radius != 3:
            params.append(f"-filter_radius {filter_radius}")
        if main_vocal != 0:
            params.append(f"-vocal {main_vocal}")
        if back_vocal != 0:
            params.append(f"-bvocal {back_vocal}")
        if music != 0:
            params.append(f"-music {music}")
        if roomsize != 0.2:
            params.append(f"-roomsize {roomsize}")
        if wetness != 0.1:
            params.append(f"-wetness {wetness}")
        if dryness != 0.85:
            params.append(f"-dryness {dryness}")
        if start == -2:
            stop_seconds = int(await set_get_config_all("Sound", "stop_milliseconds", None)) // 1000
            params.append(f"-start {stop_seconds}")
        elif start == -1 or start != 0:
            params.append(f"-start {start}")
        if output != "None":
            params.append(f"-output {output}")

        param_string = ' '.join(params)
        print("suc params")

        if audio_path:
            filename = str(random.randint(1, 1000000)) + ".mp3"
            await audio_path.save(filename)
            # Изменить ТОЛЬКО ГОЛОС
            if only_voice_change:
                try:
                    command = [
                        "python",
                        "only_voice_change_cuda0.py",
                        "-i", f"{filename}",
                        "-o", f"{filename}",
                        "-dir", str(voice),
                        "-p", f"{pitch_int}",
                        "-ir", f"{indexrate}",
                        "-fr", f"{filter_radius}",
                        "-rms", f"{roomsize}",
                        "-pro", "0.05"
                    ]
                    print("run RVC, AIName:", voice)
                    subprocess.run(command, check=True)
                    await send_file(ctx, filename, delete_file=True)
                except subprocess.CalledProcessError as e:
                    traceback_str = traceback.format_exc()
                    print(str(traceback_str))
                    await ctx.response.send_message(f"Ошибка при изменении голоса(ID:d1): {e}")
            else:
                # изменить голос без музыки
                param_string += f" -url {filename} "
                await run_main_with_settings(ctx, "робот протокол 13 " + param_string, False)
        elif url:
            if ";" in url:
                urls = url.split(";")
            elif "playlist" in url:
                urls = await get_links_from_playlist(url)
                urls = urls.split(";")
                if urls == "" or urls is None:
                    ctx.response.send_message("Ошибка нахождения видео в плейлисте")
            else:
                urls = [url]
            args = ""
            i = 0
            for one_url in urls:
                i += 1
                args += f"робот протокол 13 -url {one_url} {param_string}\n"
            await run_main_with_settings(ctx, args, True)
        else:
            await ctx.response.send_message('Не указана ссылка или аудиофайл')
            return

    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.response.send_message(f"Ошибка при изменении голоса(ID:d5) (с параметрами {param_string}): {e}")


async def agrs_with_txt(txt_file):
    try:
        filename = "temp_args.txt"
        await txt_file.save(filename)
        with open(filename, "r", encoding="utf-8") as file:
            lines = file.readlines()
            lines[-1] = lines[-1] + " "
        url = []
        name = []
        gender = []
        info = []
        speed = []
        voice_model = []
        for line in lines:
            if line.strip():
                line = line.replace(": ", ":")
                # /add_voice url:url_to_model name:some_name gender:мужчина info:some_info speed:some_speed voice_model:some_model
                pattern = r'(\w+):(.+?)\s(?=\w+:|$)'

                matches = re.findall(pattern, line)
                arguments = dict(matches)

                url.append(arguments.get('url', None))
                name.append(arguments.get('name', None))
                gender.append(arguments.get('gender', None))
                info.append(arguments.get('info', "Отсутствует"))
                speed.append(arguments.get('speed', "1"))
                voice_model.append(arguments.get('voice_model', "James"))
        return url, name, gender, info, speed, voice_model
    except Exception:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        return None, None, None, None, None, None


async def download_voice(ctx, url, name, gender, info, speed, voice_model, change_voice):
    if name == "None" or ";" in name or "/" in name or "\\" in name:
        await ctx.response.send_message('Имя не должно содержать \";\" \"/\" \"\\\" или быть None')
    # !python download_voice_model.py {url} {dir_name} {gender} {info}
    name = name.replace(" ", "_")
    if gender == "женщина":
        gender = "female"
    elif gender == "мужчина":
        gender = "male"
    else:
        gender = "male"
    try:
        command = [
            "python",
            "download_voice_model.py",
            url,
            name,
            gender,
            f"{info}",
            voice_model,
            str(speed)
        ]
        subprocess.run(command, check=True)
        voices = (await set_get_config_all("Sound", "voices")).split(";")
        voices.append(name)
        await set_get_config_all("Sound", "voices", ';'.join(voices))
        if change_voice:
            await run_main_with_settings(ctx, f"робот измени голос на {name}", True)
        await ctx.send(f"Модель {name} успешно установлена!")
    except subprocess.CalledProcessError:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.response.send_message("Ошибка при скачивании голоса.")


@bot.slash_command(name="add_voice", description='Добавить RVC голос')
async def add_voice(
        ctx: Interaction,
        url: str = SlashOption(
            name="url",
            description="Ссылка на .zip файл с моделью RVC",
            required=True
        ),
        name: str = SlashOption(
            name="name",
            description="Имя модели",
            required=True
        ),
        gender: str = SlashOption(
            name="gender",
            description="Пол (для настройки тональности)",
            required=True,
            choices=['мужчина', 'женщина']
        ),
        info: str = SlashOption(
            name="info",
            description="Какие-то сведения о данном человеке",
            required=False,
            default="Отсутствует"
        ),
        speed: float = SlashOption(
            name="speed",
            description="Ускорение/замедление голоса",
            required=False,
            default=1,
            min_value=1,
            max_value=3
        ),
        change_voice: bool = SlashOption(
            name="change_voice",
            description="(необязательно) Изменить голос на этот",
            required=False,
            default=False
        ),
        txt_file: Attachment = SlashOption(
            name="txt_file",
            description="Аудиофайл",
            required=False,
            default=None
        )
):

    await ctx.response.send_message('Выполнение...')
    if txt_file:
        urls, names, genders, infos, speeds, voice_models = await agrs_with_txt(txt_file)
        print("url:", urls)
        print("name:", names)
        print("gender:", genders)
        print("info:", infos)
        print("speed:", speeds)
        print("voice_model:", voice_models)
        for i in range(len(urls)):
            if names[i] is None:
                await ctx.send(f"Не указано имя в {i + 1} моделе")
                continue
            if urls[i] is None:
                await ctx.send(f"Не указана ссылка в {i + 1} моделе ({name})")
                continue
            if genders[i] is None:
                await ctx.send(f"Не указан пол в {i + 1} моделе ({name})")
                continue
            await download_voice(ctx, urls[i], names[i], genders[i], infos[i], speeds[i], voice_models[i], False)
        await ctx.send("Все модели успешно установлены!")
        return

    await download_voice(ctx, url, name, gender, info, speed, "None", change_voice)


@bot.command(aliases=['cmd'], help="командная строка")
async def command_line(ctx, *args):
    owner_id = await set_get_config_all("Default", "owner_id")
    if not ctx.author.id == int(owner_id):
        await ctx.author.send("Доступ запрещён")
        return

    # Получение объекта пользователя по ID
    text = " ".join(args)
    print("command line:", text)
    try:
        process = subprocess.Popen(text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        for line in stdout.decode().split('\n'):
            if line.strip():
                await ctx.author.send(line)
        for line in stderr.decode().split('\n'):
            if line.strip():
                await ctx.author.send(line)
    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.author.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.author.send(f"Произошла неизвестная ошибка: {e}")


async def run_main_with_settings(ctx, spokenText, writeAnswer):
    from function import start_bot
    await start_bot(ctx, spokenText, writeAnswer)


async def write_in_discord(ctx, text):
    from function import result_command_change, Color
    if text == "" or text is None:
        await result_command_change("ОТПРАВЛЕНО ПУСТОЕ СООБЩЕНИЕ", Color.RED)
        return
    if len(text) < 1990:
        await ctx.send(text)
    else:
        # начинает строку с "```" если оно встретилось и убирает, когда "```" опять появится
        add_format = False
        lines = text.split("\n")
        for line in lines:
            if "```" in line:
                add_format = not add_format
            if line.strip():
                if add_format:
                    line = line.replace("```", "")
                    line = "```" + line + "```"
                await ctx.send(line)


async def send_file(ctx, file_path, delete_file=False):
    try:
        await ctx.send(file=nextcord.File(file_path))
        if delete_file:
            await asyncio.sleep(1.5)
            os.remove(file_path)
    except FileNotFoundError:
        await ctx.send('Файл не найден.')
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.send(f'Произошла ошибка при отправке файла: {e}.')

async def get_voice_id_by_name(voice_name):
    with open('voices.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    voice = next((v for v in data["voices"] if v["name"] == voice_name), None)
    return voice["voice_id"] if voice else None

async def text_to_speech_file(tts, currentpitch, file_name, voice_model="Adam"):
    from elevenlabs import generate, save, set_api_key, VoiceSettings, Voice
    max_simbols = await set_get_config_all("voice", "max_simbols", None)

    pitch = 0
    if len(tts) > int(max_simbols) or await set_get_config_all("voice", "avaible_keys", None) == "None":
        print("gtts1")
        from function import gtts
        await gtts(tts, "ru", file_name)
        if currentpitch == 0:
            pitch = -12
    else:
        # получаем ключ для elevenlab
        keys = (await set_get_config_all("voice", "avaible_keys", None)).split(";")
        key = keys[0]
        if not key == "Free":
            set_api_key(key)

        stability = float(await set_get_config_all("voice", "stability"))
        similarity_boost = float(await set_get_config_all("voice", "similarity_boost"))
        style = float(await set_get_config_all("voice", "style"))
        try:
            # Arnold(быстрый) Thomas Adam Antoni !Antoni(мяг) !Clyde(тяж) !Daniel(нейтр) !Harry !James Patrick
            voice_id = await get_voice_id_by_name(voice_model)
            print("VOICE_ID_ELEVENLABS:", voice_id)
            audio = generate(
                text=tts,
                model='eleven_multilingual_v2',
                voice=Voice(
                    voice_id=voice_id,
                    settings=VoiceSettings(stability=stability, similarity_boost=similarity_boost, style=style,
                                           use_speaker_boost=True)
                ),
            )

            save(audio, file_name)
        except Exception as e:
            from function import remove_unavaible_voice_api_key
            print(f"Ошибка при выполнении команды (ID:f16): {e}")
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
            await remove_unavaible_voice_api_key()
            pitch = await text_to_speech_file(tts, currentpitch, file_name)
            return pitch
            # gtts(tts, language[:2], file_name)
    return pitch


async def create_audio_dialog(ctx: Interaction, cuda, wait_untill):
    await asyncio.sleep(cuda * 0.11 + 0.05)
    cuda = cuda % 2

    while True:
        # if int(await set_get_config_all("dialog", "files_number")) >= int(await set_get_config_all("dialog", "play_number")) + 10:
        #     await asyncio.sleep(0.5)
        #     continue
        text_path = "caversAI/dialog_create.txt"
        play_path = "caversAI/dialog_play.txt"
        with open(text_path, "r") as reader:
            line = reader.readline()
            if not line is None and not line.replace(" ", "") == "":
                await remove_line_from_txt(text_path, 1)
                name = line[line.find("-voice") + 7:].replace("\n", "")
                with open(os.path.join(f"rvc_models/{name}/gender.txt"), "r") as file:
                    pitch = 0
                    if file.read().lower() == "female":
                        pitch = 12
                filename = int(await set_get_config_all("dialog", "files_number", None))
                await set_get_config_all("dialog", "files_number", filename + 1)
                filename = "song_output/" + str(filename) + name + ".mp3"
                pitch = await text_to_speech_file(line[:line.find("-voice")], pitch, filename)
                try:
                    command = [
                        "python",
                        f"only_voice_change_cuda{cuda}.py",
                        "-i", f"{filename}",
                        "-o", f"{filename}",
                        "-dir", name,
                        "-p", f"{pitch}",
                        "-ir", "0.5",
                        "-fr", "3",
                        "-rms", "0.3",
                        "-pro", "0.15",
                        "-slow"  # значение для диалога
                    ]
                    print("run RVC, AIName:", name)
                    from function import execute_command
                    await execute_command(' '.join(command), ctx)

                    # диалог завершён.
                    print("DIALOG_TEMP:", await set_get_config_all("dialog", wait_untill, None))
                    if await set_get_config_all("dialog", wait_untill, None) == "False":
                        return

                    # применение ускорения
                    if await set_get_config_all("Sound", "change_speed", None) == "True":
                        with open(os.path.join(f"rvc_models/{name}/speed.txt"), "r") as reader:
                            speed = float(reader.read())
                            # print("SPEED:", speed)
                        from function import speed_up_audio
                        await speed_up_audio(filename, speed)
                    with open(play_path, "a") as writer:
                        writer.write(filename + "\n")
                except Exception as e:
                    traceback_str = traceback.format_exc()
                    print(str(traceback_str))
                    await ctx.send(f"Ошибка при изменении голоса(ID:d3): {e}")
            else:
                await asyncio.sleep(0.5)


async def remove_line_from_txt(file_path, delete_line):
    try:
        if not os.path.exists(file_path):
            return
        lines = []
        with open(file_path, "r") as reader:
            i = 1
            for line in reader:
                if not i == delete_line:
                    lines.append(line)
                i += 1
        with open(file_path, "w") as writer:
            for line in lines:
                writer.write(line)
    except Exception as e:
        raise f"Ошибка при удалении строки: {e}"


async def gpt_dialog(names, theme, infos, prompt_global, ctx):
    from function import chatgpt_get_result
    # Делаем диалог между собой
    if await set_get_config_all("dialog", "dialog", None) == "True":
        prompt = (f"Привет, chatGPT. Вы собираетесь сделать диалог между {', '.join(names)}. На тему \"{theme}\". "
                  f"персонажи должны соответствовать своему образу насколько это возможно. "
                  f"{'.'.join(infos)}. {prompt_global}. "
                  f"Обязательно в конце диалога напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                  f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
        result = (await chatgpt_get_result(prompt, ctx)).replace("[", "").replace("]", "")
        # await write_in_discord(ctx, result)
        with open("caversAI/dialog_create.txt", "a") as writer:
            for line in result.split("\n"):
                for name in names:
                    # Человек: привет
                    # Человек (man): привет
                    if line.startswith(name):
                        line = line[line.find(":") + 1:]
                        writer.write(line + f"-voice {name}\n")

        while await set_get_config_all("dialog", "dialog", None) == "True":
            try:
                if "\n" in result:
                    result = result[result.rfind("\n"):]
                spoken_text = ""
                spoken_text_config = await set_get_config_all("dialog", "user_spoken_text", None)
                if not spoken_text_config == "None":
                    spoken_text = "Отвечайт зрителям! Зрители за прошлый диалог написали:\"" + spoken_text_config + "\""
                    await set_get_config_all("dialog", "user_spoken_text", "None")
                random_int = random.randint(1, 33)
                if not random_int == 0:
                    prompt = (f"Привет chatGPT, продолжи диалог между {', '.join(names)}. "
                              f"{'.'.join(infos)}. {prompt_global} "
                              f"персонажи должны соответствовать своему образу насколько это возможно. "
                              f"Никогда не пиши приветствие в начале этого диалога. "
                              f"Никогда не повторяй то, что было в прошлом диалоге! Вот что было в прошлом диалоге:\"{result}\". {spoken_text}"
                              f"\nОбязательно в конце напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                              f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
                else:
                    prompt = (
                        f"Привет, chatGPT. Вы собираетесь сделать диалог между {', '.join(names)} на случайную тему,"
                        f" которая должна относиться к событиям сервера. "
                        f"Персонажи должны соответствовать своему образу насколько это возможно. "
                        f"Никогда не пиши приветствие в начале этого диалога. "
                        f"{'.'.join(infos)}. {prompt_global}. {spoken_text}"
                        f"Обязательно в конце напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                        f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
                print("PROMPT:", prompt)
                result = (await chatgpt_get_result(prompt, ctx)).replace("[", "").replace("]", "")
                # await write_in_discord(ctx, result)
                with open("caversAI/dialog_create.txt", "a") as writer:
                    for line in result.split("\n"):
                        for name in names:
                            # Человек: привет
                            # Человек (man): привет
                            if line.startswith(name):
                                line = line[line.find(":") + 1:]
                                writer.write(line + f"-voice {name}\n")
                                break
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(str(traceback_str))
                await ctx.send(f"Ошибка при изменении голоса(ID:d4): {e}")



async def play_dialog(ctx: Interaction):
    number = int(await set_get_config_all("dialog", "play_number", None))
    while await set_get_config_all("dialog", "dialog", None) == "True":
        try:
            files = os.listdir("song_output")
            files = sorted(files)
            for file in files:
                if file.startswith(str(number)):
                    with open("caversAI/dialog_play.txt", "r") as reader:
                        lines = reader.read()
                        if file not in lines:
                            await asyncio.sleep(0.1)
                            continue
                    from function import playSoundFile
                    number += 1
                    await set_get_config_all("dialog", "play_number", number)
                    speaker = file[:file.find(".")]
                    speaker = re.sub(r'\d', '', speaker)
                    await ctx.send("говорит " + speaker)
                    await ("song_output/" + file, -1, 0, ctx)
                    os.remove("song_output/" + file)
                    await ctx.send("end")
                else:
                    await asyncio.sleep(0.2)
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
            await ctx.send(f"Ошибка при изменении голоса(ID:d2): {e}")

@bot.slash_command(name="create_dialog", description='Имитировать диалог людей')
async def create_dialog(
    ctx : Interaction,
    names: str = SlashOption(
        name="names",
        description="Участники диалога через ';' (у каждого должен быть добавлен голос!)",
        required=True
    ),
    theme: str = SlashOption(
        name="theme",
        description="Начальная тема разговора",
        required=False,
        default="случайная тема"
    ),
    prompt: str = SlashOption(
        name="prompt",
        description="Общий запрос для всех диалогов",
        required=False,
        default=""
    )
):
    try:

        await ctx.response.send_message('Бот выводит диалог только в голосовом чате. Используйте /join')

        if await set_get_config_all("dialog", "dialog", None) == "True":
            await ctx.response.send_message("Уже идёт диалог!")
            return
        # отчищаем прошлые диалоги
        with open("caversAI/dialog_create.txt", "w"):
            pass
        with open("caversAI/dialog_play.txt", "w"):
            pass
        voices = (await set_get_config_all("Sound", "voices")).replace("\"", "").replace(",", "").split(";")
        voices.remove("None")  # убираем, чтобы не путаться
        names = names.split(";")
        if len(names) < 2:
            await ctx.response.send_message("Должно быть как минимум 2 персонажа")
            return
        infos = []
        for name in names:
            if name not in voices:
                await ctx.response.send_message("Выберите голоса из списка: " + ';'.join(voices))
                return
            with open(f"rvc_models/{name}/info.txt") as reader:
                file_content = reader.read().replace("Вот информация о тебе:", "")
                infos.append(f"Вот информация о {name}: {file_content}")
        await set_get_config_all("dialog", "dialog", "True")
        await set_get_config_all("gpt", "gpt_mode", "None")
        # names, theme, infos, prompt, ctx
        # запустим сразу 8 процессов для обработки голоса
        await asyncio.gather(gpt_dialog(names, theme, infos, prompt, ctx), play_dialog(ctx),
                             create_audio_dialog(ctx, 0, "dialog"), create_audio_dialog(ctx, 1, "dialog"),
                             create_audio_dialog(ctx, 2, "dialog"), create_audio_dialog(ctx, 3, "dialog"))
        """
                             create_audio_dialog(ctx, 4, "dialog"), create_audio_dialog(ctx, 5, "dialog"),
                             create_audio_dialog(ctx, 6, "dialog"), create_audio_dialog(ctx, 7, "dialog")
                            """
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.response.send_message(f"Ошибка при диалоге: {e}")


voiceClient = None
paused = False


@bot.slash_command(description="Joins a voice channel")
async def join(interaction: nextcord.Interaction, *, channel: nextcord.VoiceChannel):
    """Joins a voice channel"""

    global voiceClient
    try:
        voiceClient = await channel.connect()
    except nextcord.errors.ApplicationInvokeError:
        await voiceClient.disconnect()
        voiceClient = await channel.connect()
    await interaction.send(f"Joined {channel.name}")


@bot.slash_command(description="Plays a file from the local filesystem")
async def play(interaction: nextcord.Interaction, *, query):
    """Plays a file from the local filesystem"""

    global voiceClient
    global paused

    if voiceClient is None:
        if interaction.user.voice:
            await join(interaction, channel=interaction.user.voice.channel)
        else:
            await interaction.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")

    source = nextcord.PCMVolumeTransformer(nextcord.FFmpegPCMAudio(query))
    voiceClient.play(source, after=lambda e: print(f"Player error: {e}") if e else None)

    await interaction.send(f"Now playing: {query}")


@bot.slash_command(description="Changes the player's volume")
async def volume(interaction: nextcord.Interaction, volume: int):
    """Changes the player's volume"""

    global voiceClient

    if voiceClient is None:
        return await interaction.send("Not connected to a voice channel.")

    voiceClient.source.volume = volume / 100
    await interaction.send(f"Changed volume to {volume}%")


@bot.slash_command(description="Pauses music playback")
async def pause(interaction: nextcord.Interaction):
    """Pauses music playback"""

    global voiceClient
    global paused

    if voiceClient.is_playing():
        paused = True
        voiceClient.pause()
        await interaction.send("Paused.")
    else:
        await interaction.send("There isn't any music to pause.")


@bot.slash_command(description="Resumes playing on voice")
async def resume(interaction: nextcord.Interaction):
    """Resumes music playback"""

    global voiceClient
    global paused

    async with interaction.channel.typing():
        pass
    if paused:
        voiceClient.resume()
        await interaction.send("Resumed.")
        paused = False
    else:
        await interaction.send("There isn't any music to resume.")


@bot.slash_command(description="Stops and disconnects the bot from voice")
async def stop(interaction: nextcord.Interaction):
    """Stops and disconnects the bot from voice"""

    global voiceClient
    await voiceClient.disconnect()
    await interaction.send("Disconnected.")


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore")

    print("update 2")
    try:

        arguments = sys.argv

        if len(arguments) > 1:
            discord_token = arguments[1]

            print("====load bot====")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(bot.start(discord_token))
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        print(f"Произошла ошибка: {e}")
