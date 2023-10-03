import multiprocessing
import time
import configparser

import pyaudio
import discord
from discord.ext import commands
import asyncio
import sys

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

bot = commands.AutoShardedBot(intents=discord.Intents.all(), command_prefix="\\")


async def main():
    await bot.start(discord_token)


@bot.event
async def on_ready():
    from GPT_runner import run, model_loaded
    pool = multiprocessing.Pool(processes=1)
    pool.apply_async(run)
    pool.close()
    while not model_loaded:
        await asyncio.sleep(1)
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
        # await recognize(ctx) - звук из микрофона! (локально)
    else:
        await ctx.message.reply(voiceChannelErrorText)


@bot.command(aliases=['Disconnect', 'DISCONNECT', 'DC', 'dc', 'Dc'])
async def disconnect(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


@bot.command(help="сказать роботу текст")
async def say(ctx, *args):
    message = " ".join(args)
    from function import replace_mat_in_sentence
    if not default_settings.get("robot_name_need"):
        print(message)
        message = "робот " + message
    else:
        print(message)
    message = await replace_mat_in_sentence(message)
    # Проверяем, находится ли автор команды в войс-чате
    if ctx.author.voice:
        # Получаем войс-канал автора команды
        voice_channel = ctx.author.voice.channel
        # Проверяем, находится ли бот уже в каком-либо войс-чате
        if ctx.voice_client is None:
            # Если бот не находится в войс-чате, подключаем его
            await voice_channel.connect()
        else:
            # Если бот уже находится в войс-чате, перемещаем его в новый войс-канал
            await ctx.voice_client.move_to(voice_channel)
        await run_main_with_settings(ctx, message, True)
    else:
        await ctx.send("Вы должны находиться в войс-чате, чтобы использовать эту команду.")


stop_milliseconds = 0


@bot.command(help="пауза")
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


@bot.command(help="пропуск")
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Текущий трек пропущен ⏭️")
        stop_milliseconds = 0
    else:
        await ctx.send("Нет активного аудио для пропуска.")


stopRecognize = False


async def recognize(ctx):
    import vosk
    from function import setModelWithLanguage, replace_numbers_in_sentence
    languageWas = ""
    rec = ""
    vosk.SetLogLevel(0)

    while True:
        if stopRecognize:
            time.sleep(0.1)
            continue

        # Изменяем модель, если необходимо (+ в начале)
        language = default_settings.get("language")
        if languageWas != language:
            languageWas = language
            print(language)
            model_path = setModelWithLanguage(language, "stt")
            print(model_path, "- Model")
            model = vosk.Model(model_path)
            rec = vosk.KaldiRecognizer(model, 16000)
            rec.SetWords(True)
            rec.SetPartialWords(True)

        p = pyaudio.PyAudio()
        stream = await get_microphone_stream("стерео")

        while True:
            data = stream.read(4096)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                spokenText = rec.Result()
                spokenText = spokenText[spokenText.find(":") + 3:spokenText.find("\"", spokenText.find(":") + 3)]
                spokenText = replace_numbers_in_sentence(spokenText)
                if spokenText:
                    print(spokenText)
                    await run_main_with_settings(ctx, spokenText)
                    pass
            else:
                print(rec.PartialResult())
        stream.stop_stream()
        stream.close()
        p.terminate()


async def get_microphone_stream(microphone_name):
    frames_per_buffer = 4096
    sample_rate = 16000
    p = pyaudio.PyAudio()

    # получить микрофоны
    input_devices = []
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        if device_info['maxInputChannels'] > 0:
            input_devices.append(device_info)

    # Поиск микрофона
    selected_microphone = None
    for device_info in input_devices:
        if microphone_name in device_info['name'].lower():
            selected_microphone = device_info
            break

    if selected_microphone:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=int(selected_microphone['index']),
            frames_per_buffer=frames_per_buffer
        )
        return stream
    else:
        raise Exception("нет такого микрофона")


async def run_main_with_settings(ctx, spokenText, writeAnswer):
    from function import start_bot
    await start_bot(ctx, spokenText, writeAnswer)


async def write_in_discord(ctx, text):
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
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
    else:
        print("Укажите discord_TOKEN")
        exit(-1)
    bot.run(discord_token)
