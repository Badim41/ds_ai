import asyncio
import nextcord
import os
import random
import re
import subprocess
import sys
import traceback
from nextcord import Interaction, SlashOption
from nextcord.ext import commands
from pytube import Playlist

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
        await interaction.response.send_message(f"Ошибка при изменении конфига (с параметрами{section},{key},{value}): {e}")

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
    ctx : Interaction,
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
    )
):
    audio_path = ctx.message.attachments[0]
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
        url = []
        name = []
        gender = []
        info = []
        speed = []
        voice_model = []
        for line in lines:
            if line.strip():
                # забейте, просто нужен пробел и всё
                line += " "
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
    ctx : Interaction,
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
    )
):
    txt_file = ctx.message.attachments[0]

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
