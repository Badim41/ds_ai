import sys;
import time
from modifed_sinks import StreamSink
import configparser
import speech_recognition as sr
import asyncio
import os
from pathlib import Path
sys.path.insert(0, 'discord.py')
import discord


config = configparser.ConfigParser()
config.read('config.ini')

connections = {}

stream_sink = StreamSink()


async def set_get_config(key="record", value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.getboolean("Sound", key)
    config.set('Sound', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def record(ctx):  # if you're using commands.Bot, this will also work.
    voice = ctx.author.voice

    if not voice:
        await ctx.reply("You aren't in a voice channel, get your life together lmao")
        return

    vc = None

    # если бот УЖЕ в войс-чате
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        if vc.channel != voice.channel:
            await vc.move_to(voice.channel)
    # если бот НЕ в войс-чате
    if not vc:
        stream_sink.set_user(ctx.author.id)
        vc = await voice.channel.connect()
        connections[ctx.guild.id] = vc

    # Начинаем запись
    voice.start_recording(
        stream_sink,  # the sink type to use.
        once_done,  # what to do once done.
        ctx.channel  # the channel to disconnect from.
    )
    await set_get_config(value=True)
    await ctx.reply("Started listening.")
    await recognize(ctx)


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await set_get_config(value=False)
    await sink.vc.disconnect()  # disconnect from the voice channel.
    print("Stopped listening.")


file_not_found_in_raw = 0
recognized_text = ""
WAIT_FOR_ANSWER_IN_SECONDS = 3

async def recognize(ctx):
    global file_not_found_in_raw, recognized_text, WAIT_FOR_ANSWER_IN_SECONDS
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recognizer = sr.Recognizer()
    while True:
        if not await set_get_config():
            return
        file_found = None
        for filename in os.listdir(project_dir):
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
                    from discord_bot import run_main_with_settings
                    await run_main_with_settings(ctx, recognized_text, True)
                    recognized_text = ""
            continue
        print("file found")
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
        print(f'Файл {Path(file_found)} удален')

    print("Stop_Recording")


async def stop_recording(ctx):
    if ctx.guild.id in connections:  # check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        # stop recording, and call the callback (once_done).
        vc.stop_recording()
        del connections[ctx.guild.id]  # remove the guild from the cache.
    else:
        await ctx.reply("Я и так тебя не слушал ._.")
