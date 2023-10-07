import multiprocessing
import os
import subprocess
import configparser
import asyncio
import wave

from pydub import AudioSegment

from discord import Option
from modifed_sinks import StreamSink
import speech_recognition as sr
from pathlib import Path
import sys
import discord
from discord.ext import commands

# Значения по умолчанию
voiceChannelErrorText = '❗ Вы должны находиться в голосовом канале ❗'
config = configparser.ConfigParser()

connections = {}

stream_sink = StreamSink()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)


async def set_get_config(key="record", value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.getboolean("Sound", key)
    config.set('Sound', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def set_get_config_default(key, value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.get("Default", key)
    config.set('Default', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


@bot.event
async def on_ready():
    print('Status: online')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='AI-covers'))


@bot.slash_command(name="join", description='присоединиться к голосовому каналу')
async def join(ctx):
    if ctx.message.author.voice:
        if not ctx.voice_client:
            await ctx.message.author.voice.channel.connect(reconnect=True)
        else:
            await ctx.voice_client.move_to(ctx.message.author.voice.channel)
    else:
        await ctx.message.send(voiceChannelErrorText)


@bot.slash_command(name="record", description='воспринимать команды из микрофона')
async def record(ctx):  # if you're using commands.Bot, this will also work.
    voice = ctx.author.voice

    if not voice:
        # hehe
        await ctx.send("You aren't in a voice channel, get your life together lmao")

    vc = None  # Инициализируем переменную для хранения подключения к войс-чату.

    # если бот УЖЕ в войс-чате
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        if vc.channel != voice.channel:
            await vc.move_to(voice.channel)
    # если бота НЕТ в войс-чате
    if not vc:
        stream_sink.set_user(ctx.author.id)
        vc = await voice.channel.connect()
        connections[ctx.guild.id] = vc

    # Начинаем запись
    vc.start_recording(
        stream_sink,  # the sink type to use.
        once_done,  # what to do once done.
        ctx.channel  # the channel to disconnect from.
    )
    await set_get_config(value=True)
    await ctx.send("Started listening.")
    await recognize(ctx)


@bot.slash_command(name="stop_recording", description='перестать воспринимать команды из микрофона')
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        # stop recording, and call the callback (once_done).
        vc.stop_recording()
        del connections[ctx.guild.id]  # remove the guild from the cache.
    else:
        await ctx.send("Я и так тебя не слушал ._.")


@bot.slash_command(name="disconnect", description='выйти из войс-чата')
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


# @bot.command(help="сказать роботу текст")
# async def say(ctx, *args):
#     message = " ".join(args)
#     from function import replace_mat_in_sentence
#     if not default_settings.get("robot_name_need"):
#         message = default_settings.get("currentAIname") + ", " + message
#         print(message)
#     else:
#         print(message)
#     message = await replace_mat_in_sentence(message)
#     # Проверяем, находится ли автор команды в войс-чате
#     # if ctx.author.voice:
#     if True:
#         # Получаем войс-канал автора команды
#         # voice_channel = ctx.author.voice.channel
#         # # Проверяем, находится ли бот уже в каком-либо войс-чате
#         # if ctx.voice_client is None:
#         #     # Если бот не находится в войс-чате, подключаем его
#         #     await voice_channel.connect()
#         # else:
#         #     # Если бот уже находится в войс-чате, перемещаем его в новый войс-канал
#         #     await ctx.voice_client.move_to(voice_channel)
#         await run_main_with_settings(ctx, message, True)
#     else:
#         await ctx.send("Вы должны находиться в войс-чате, чтобы использовать эту команду.")


stop_milliseconds = 0


@bot.slash_command(name="pause", description='пауза/воспроизведение')
async def pause(ctx):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Пауза ⏸")
    elif voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Продолжаем воспроизведение ▶️")
    else:
        await ctx.send("Нет активного аудио для приостановки или продолжения.")


@bot.slash_command(name="skip", description='пропуск аудио')
async def skip(ctx):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    global stop_milliseconds
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Текущий трек пропущен ⏭️")
        stop_milliseconds = 0
    else:
        await ctx.send("Нет активного аудио для пропуска.")


@bot.slash_command(name="lenght", description='Длина запроса')
async def __lenght(
        ctx,
        number: Option(int, description='Длина запроса для GPT (Число от 1 до 1000)', required=True, min_value=1,
                       max_value=1000)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    # for argument in (number,"""boolean, member, text, choice"""):
    print(f'{number} ({type(number).__name__})\n')
    await run_main_with_settings(ctx, f"робот длина запроса{number}", True)
    await ctx.send(f"Длина запроса: {number}")


@bot.slash_command(name="say", description='Сказать роботу что-то')
async def __say(
        ctx,
        text: Option(str, description='Сам текст/команда. Список команд: \\help-say', required=True)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    from function import replace_mat_in_sentence
    if await set_get_config_default("robot_name_need") == "False":
        text = await set_get_config_default("currentainame") + ", " + text
    text = await replace_mat_in_sentence(text)
    print(f'{text} ({type(text).__name__})\n')
    await run_main_with_settings(ctx, text, True)


folders = []


@bot.slash_command(name="tts", description='_Заставить_ бота говорить всё, что захочешь')
async def __tts(
        ctx,
        text: Option(str, description='Текст для озвучки', choices=folders, required=True),
        ai_voice: Option(str, description='Голос для озвучки', required=False, default=None)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    from function import replace_mat_in_sentence, mat_found, text_to_speech
    text = await replace_mat_in_sentence(text)
    if mat_found:
        await ctx.send("Такое нельзя произносить!")
        return
    print(f'{text} ({type(text).__name__})\n')
    if ai_voice is None:
        ai_voice = await set_get_config_default("currentainame")
    await text_to_speech(text, False, ctx, ai_dictionary=ai_voice)


@bot.slash_command(name="ai_cover", description='_Заставить_ бота озвучить видео/спеть песню')
async def __cover(
        ctx,
        url: Option(str, description='Ссылка на видео', required=True),
        voice: Option(str, description='Голос для видео', required=False, default=None),
        pitch: Option(int, description='Тональность (от -2 до 2)', required=False, default=0, min_value=-2, max_value=2),
        time: Option(int, description='Время (мин. 0)', required=False, default=-1, min_value=0),
        indexrate: Option(float, description='Индекс частоты (от 0 до 1)', required=False, default=0.5, min_value=0, max_value=1),
        loudness: Option(float, description='Громкость (от 0 до 1)', required=False, default=0.2, min_value=0, max_value=1),
        main_vocal: Option(int, description='Громкость основного вокала (от -20 до 0)', required=False, default=0, min_value=-20, max_value=0),
        back_vocal: Option(int, description='Громкость бэквокала (от -20 до 0)', required=False, default=0, min_value=-20, max_value=0),
        music: Option(int, description='Громкость музыки (от -20 до 0)', required=False, default=0, min_value=-20, max_value=0),
        roomsize: Option(float, description='Размер помещения (от 0 до 1)', required=False, default=0.2, min_value=0, max_value=1),
        wetness: Option(float, description='Влажность (от 0 до 1)', required=False, default=0.1, min_value=0, max_value=1),
        dryness: Option(float, description='Сухость (от 0 до 1)', required=False, default=0.85, min_value=0, max_value=1),
        start: Option(int, description='Начало (минимальное значение 0)', required=False, default=0, min_value=0),
        output: Option(bool, description='Отправить результат в архиве', required=False, default=False)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    if voice is None:
        voice = await set_get_config_default("currentAIname")
    params = []
    if url:
        params.append(f"-url {url}")
    if voice:
        params.append(f"-voice {voice}")
    if pitch != 0:
        params.append(f"-pitch {pitch}")
    if time != -1:
        params.append(f"-time {time}")
    if indexrate != 0.5:
        params.append(f"-indexrate {indexrate}")
    if loudness != 0.2:
        params.append(f"-loudness {loudness}")
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
    if start != 0:
        params.append(f"-start {start}")
    param_string = ' '.join(params)

    await run_main_with_settings(ctx, "робот протокол 13 " + param_string, False)
    # output..

@bot.slash_command(name="add_voice", description='Добавить RVC голос')
async def __add_voice(
        ctx,
        url: Option(str, description='Ссылка на .zip файл с моделью RVC', required=True),
        name: Option(str, description=f'Имя модели', required=True),
        gender: Option(str, description=f'Пол (для настройки тональности)', required=True,
                       choices=['мужчина', 'женщина']),
        info: Option(str, description=f'(необязательно) Какие-то сведения о данном человеке', required=False,
                     default="Отсутствует")
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    # !python download_model_with_link_AICoverGen.py {url} {dir_name} {gender} {info}
    command = None
    if gender == "женщина":
        gender = "female"
    elif gender == "мужчина":
        gender = "male"
    else:
        gender = "male"
    try:
        command = [
            "python",
            "download_model_with_link_AICoverGen.py",
            url,
            name,
            gender,
            info
        ]
        subprocess.run(command, check=True)
        global folders
        folders.append(name)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка при скачивании голоса {command}: {e}")


@bot.command(aliases=['cmd'], help="командная строка")
async def command_line(ctx, *args):
    text = " ".join(args)
    try:
        process = subprocess.Popen(text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        for line in stdout.decode().split('\n'):
            if line.strip():
                await ctx.send(line)
        for line in stderr.decode().split('\n'):
            if line.strip():
                await ctx.send(line)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        await ctx.send(f"Произошла неизвестная ошибка: {e}")


@bot.command(aliases=['прослушай_кеклола'], help="ХАВХВАХВАХВАХВАХ")
async def i_hear_you(ctx):  # if you're using commands.Bot, this will also work.
    await ctx.send("Получаю базу данных пользователей")
    await asyncio.sleep(1)
    await ctx.send("Пользователь <@920404602317324388> найден!")
    await asyncio.sleep(1)
    await ctx.send("Получен аудиопоток микрофона!")


async def run_main_with_settings(ctx, spokenText, writeAnswer):
    from function import start_bot
    await start_bot(ctx, spokenText, writeAnswer)


async def write_in_discord(ctx, text):
    # await run_main_with_settings(ctx, text, True)
    await ctx.send(text)


async def playSoundFileDiscord(ctx, audio_file_path, duration, start_seconds):
    # Проверяем, находится ли бот в голосовом канале
    if not ctx.voice_client:
        await ctx.send("Бот не находится в голосовом канале. Используйте команду `join`, чтобы присоединить его.")
        return
    source = discord.FFmpegPCMAudio(audio_file_path, options=f"-ss {start_seconds} -t {duration}")

    # Проигрываем файл
    ctx.voice_client.play(source)

    # Ожидаем окончания проигрывания
    global stop_milliseconds
    while ctx.voice_client.is_playing():
        await asyncio.sleep(1)
        stop_milliseconds += 1000


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await set_get_config(value=False)
    await sink.vc.disconnect()  # disconnect from the voice channel.
    print("Stopped listening.")


file_not_found_in_raw = 0
WAIT_FOR_ANSWER_IN_SECONDS = 1.5


async def recognize(ctx):
    global file_not_found_in_raw, WAIT_FOR_ANSWER_IN_SECONDS
    mp3_filename = "out_all.mp3"
    recognizer = sr.Recognizer()
    while True:
        if not await set_get_config():
            print("Stopped listening2.")
            return
        file_found = None
        for filename in os.listdir(os.getcwd()):
            if filename.startswith("output") and filename.endswith(".mp3"):
                file_found = filename
                break
        if file_found is None:
            await asyncio.sleep(0.1)
            file_not_found_in_raw += 1

            if file_not_found_in_raw > WAIT_FOR_ANSWER_IN_SECONDS * 10:
                stream_sink.cleanup()
                file_not_found_in_raw = 0
                with sr.AudioFile(mp3_filename) as source:
                    audio_data = recognizer.record(source)
                    try:
                        text = recognizer.recognize_google(audio_data, language="ru-RU")
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"Ошибка: {e}")
                Path(mp3_filename).unlink()
                from function import replace_mat_in_sentence, replace_numbers_in_sentence
                text = await replace_numbers_in_sentence(text)
                text = await replace_mat_in_sentence(text)
                print(text)
                await run_main_with_settings(ctx, text, True)
                # создание пустого файла
                with wave.open(mp3_filename, 'w') as wf:
                    wf.setparams((0, 0, 0, 0, 'NONE', 'not compressed'))
                with open(mp3_filename, 'wb') as f:
                    f.write(b'\xFF\xFB')
            continue
        result = AudioSegment.from_file(file_found, format="mp3") + AudioSegment.from_file(mp3_filename, format="mp3")
        result.export(mp3_filename, format="mp3")

    print("Stop_Recording")


if __name__ == "__main__":
    print("update 1")
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
    else:
        print("Укажите discord_TOKEN")
        exit(-1)
    from GPT_runner import run

    pool = multiprocessing.Pool(processes=1)
    pool.apply_async(run)
    pool.close()
    bot.run(discord_token)
