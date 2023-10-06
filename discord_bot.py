import multiprocessing
import os
import subprocess
import time
import configparser
import pyaudio
import asyncio
from modifed_sinks import StreamSink
import speech_recognition as sr
from pathlib import Path
import sys
import discord
from discord.ext import commands


# Значения по умолчанию
voiceChannelErrorText = '❗ Вы должны находиться в голосовом канале ❗'
config = configparser.ConfigParser()
config.read('config.ini')
default_settings = {
    "language": config.get('Default', 'language'),
    "prompt_length": config.getint('Default', 'prompt_length'),
    "admin": config.getboolean('Default', 'admin'),
    "all_admin": config.getboolean('Default', 'all_admin'),
    "video_length": config.getint('Default', 'video_length'),
    "currentAIname": config.get('Default', 'currentAIname'),
    "currentAIinfo": config.get('Default', 'currentAIinfo'),
    "currentAIpitch": config.getint('Default', 'currentAIpitch'),
    "robotNameNeed": config.getboolean('Default', 'robotNameNeed')
}
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


@bot.event
async def on_ready():
    print('Status: online')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='AI-covers'))


@bot.command(aliases=['j', 'J', 'Join', 'JOIN'], help="присоединиться к голосовому каналу")
async def join(ctx):
    if ctx.message.author.voice:
        if not ctx.voice_client:
            await ctx.message.author.voice.channel.connect(reconnect=True)
        else:
            await ctx.voice_client.move_to(ctx.message.author.voice.channel)
    else:
        await ctx.message.send(voiceChannelErrorText)



@bot.command(aliases=['прослушай_кеклола'], help="ХАВХВАХВАХВАХВАХ")
async def i_hear_you(ctx):  # if you're using commands.Bot, this will also work.
    await ctx.send("Получаю базу данных пользователей")
    await asyncio.sleep(1)
    await ctx.send("Пользователь <@920404602317324388> найден!")
    await asyncio.sleep(1)
    await ctx.send("Получен аудиопоток микрофона!")


@bot.command(aliases=['rec', 'REC'], help="воспринимать команды из своего микрофона")
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


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await set_get_config(value=False)
    await sink.vc.disconnect()  # disconnect from the voice channel.
    print("Stopped listening.")


file_not_found_in_raw = 0
recognized_text = ""
WAIT_FOR_ANSWER_IN_SECONDS = 1.5

async def recognize(ctx):
    global file_not_found_in_raw, recognized_text, WAIT_FOR_ANSWER_IN_SECONDS
    recognizer = sr.Recognizer()
    while True:
        if not await set_get_config():
            print("Stopped listening2.")
            return
        file_found = None
        for filename in os.listdir(os.getcwd()):
            if filename.startswith("output") and filename.endswith(".wav"):
                file_found = filename
                break
        if file_found is None:
            await asyncio.sleep(0.1)
            file_not_found_in_raw += 1

            if file_not_found_in_raw > WAIT_FOR_ANSWER_IN_SECONDS*10:
                stream_sink.cleanup()
                if not recognized_text == "":
                    from function import replace_mat_in_sentence, replace_numbers_in_sentence
                    recognized_text = await replace_numbers_in_sentence(recognized_text)
                    recognized_text = await replace_mat_in_sentence(recognized_text)
                    print(recognized_text)
                    await run_main_with_settings(ctx, recognized_text, True)
                    recognized_text = ""
            continue
        # print("file found")
        file_not_found_in_raw = 0

        with sr.AudioFile(file_found) as source:
            audio_data = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                recognized_text += text + " "
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Ошибка: {e}")
        Path(file_found).unlink()
        # print(f'Файл {Path(file_found)} удален')

    print("Stop_Recording")

@bot.command(aliases=['srec', 'SREC'], help="перестать воспринимать команды из своего микрофона")
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        # stop recording, and call the callback (once_done).
        vc.stop_recording()
        del connections[ctx.guild.id]  # remove the guild from the cache.
    else:
        await ctx.send("Я и так тебя не слушал ._.")


@bot.command(aliases=['Disconnect', 'DISCONNECT', 'DC', 'dc', 'Dc'])
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


@bot.command(help="сказать роботу текст")
async def say(ctx, *args):
    message = " ".join(args)
    from function import replace_mat_in_sentence
    if not default_settings.get("robot_name_need"):
        message = default_settings.get("currentAIname") + ", " + message
        print(message)
    else:
        print(message)
    message = await replace_mat_in_sentence(message)
    # Проверяем, находится ли автор команды в войс-чате
    # if ctx.author.voice:
    if True:
        # Получаем войс-канал автора команды
        # voice_channel = ctx.author.voice.channel
        # # Проверяем, находится ли бот уже в каком-либо войс-чате
        # if ctx.voice_client is None:
        #     # Если бот не находится в войс-чате, подключаем его
        #     await voice_channel.connect()
        # else:
        #     # Если бот уже находится в войс-чате, перемещаем его в новый войс-канал
        #     await ctx.voice_client.move_to(voice_channel)
        await run_main_with_settings(ctx, message, True)
    else:
        await ctx.send("Вы должны находиться в войс-чате, чтобы использовать эту команду.")


stop_milliseconds = 0


@bot.command(aliases=['пауза'], help="пауза")
async def pause(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Пауза ⏸")
    elif voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Продолжаем воспроизведение ▶️")
    else:
        await ctx.send("Нет активного аудио для приостановки или продолжения.")


@bot.command(aliases=['скип'], help="пропуск")
async def skip(ctx):
    global stop_milliseconds
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Текущий трек пропущен ⏭️")
        stop_milliseconds = 0
    else:
        await ctx.send("Нет активного аудио для пропуска.")


@bot.command(aliases=['cmd'], help="командная строка")
async def command_line(ctx, *args):
    text = " ".join(args)
    try:
        process = subprocess.Popen(text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()

        for line in stdout.decode().split('\n'):
            await ctx.send(line)
        for line in stderr.decode().split('\n'):
            await ctx.send(line)

    except (subprocess.CalledProcessError, IOError, Exception):
        pass



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

    # Создаем аудиофайл для проигрывания

    source = discord.FFmpegPCMAudio(audio_file_path, options=f"-ss {start_seconds} -t {duration}")

    # Проигрываем аудиофайл
    ctx.voice_client.play(source)

    # Ожидаем окончания проигрывания
    global stop_milliseconds
    while ctx.voice_client.is_playing():
        await asyncio.sleep(1)
        stop_milliseconds += 1000


if __name__ == "__main__":
    print("update 3")
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
