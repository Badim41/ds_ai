import asyncio
import multiprocessing
import os
import time
import wave
from pathlib import Path

import discord
from discord.ext import commands
from test2 import StreamSink
import sys
import configparser
import speech_recognition as sr

config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

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


@bot.command()
async def record(ctx):  # if you're using commands.Bot, this will also work.
    voice = ctx.author.voice

    if not voice:
        # hehe
        await ctx.reply("You aren't in a voice channel, get your life together lmao")

    # connect to the voice channel the author is in.
    stream_sink.set_user(ctx.author.id)
    vc = await voice.channel.connect()
    # updating the cache with the guild and channel.
    connections.update({ctx.guild.id: vc})

    vc.start_recording(
        stream_sink,  # the sink type to use.
        once_done,  # what to do once done.
        ctx.channel  # the channel to disconnect from.
    )
    await set_get_config(value=True)
    await ctx.reply("Started listening.")
    await recognize(ctx)


# our voice client already passes these in.
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
        if not set_get_config():
            return
        file_found = None
        for filename in os.listdir(project_dir):
            if filename.startswith("output") and filename.endswith(".wav"):
                file_found = filename
                break
        if file_found is None:
            await asyncio.sleep(0.1)
            file_not_found_in_raw += 1
            if file_not_found_in_raw > WAIT_FOR_ANSWER_IN_SECONDS*10 and not recognized_text == "":
                print(recognized_text)
                await ctx.reply(recognized_text)
                recognized_text = ""
            continue
        print("file found")
        file_not_found_in_raw = 0

        with sr.AudioFile(file_found) as source:
            audio_data = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                recognized_text += text
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Ошибка: {e}")
        Path(file_found).unlink()
        print(f'Файл {Path(file_found)} удален')

    print("Stop_Recording")


@bot.command()
async def stop_recording(ctx):
    if ctx.guild.id in connections:  # check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        # stop recording, and call the callback (once_done).
        vc.stop_recording()
        del connections[ctx.guild.id]  # remove the guild from the cache.
    else:
        # respond with this if we aren't listening
        await ctx.reply("I am currently not listening here.")


if __name__ == "__main__":
    print("update 3")
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
    else:
        print("Укажите discord_TOKEN")
        exit(-1)
    bot.run(discord_token)
