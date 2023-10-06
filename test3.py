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
from vosk import Model, KaldiRecognizer
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

connections = {}

stream_sink = StreamSink()


async def is_record(value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.getboolean("Sound", "record")
    config.set('Sound', "record", str(value))
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
    await is_record(value=True)
    await ctx.reply("Started listening.")
    await recognize(ctx)


# our voice client already passes these in.
async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await is_record(value=False)
    await sink.vc.disconnect()  # disconnect from the voice channel.
    print("Stopped listening.")

async def recognize(ctx):
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    while True:
        config.read('config.ini')
        if not config.getboolean("Sound", "record"):
            return
        file_found = None
        for filename in project_dir:
            if filename.startswith("output") and filename.endswith(".wav"):
                file_found = filename
                break
        if file_found is None:
            await asyncio.sleep(0.1)
            continue
        print("file found")
        model = Model(lang="ru")
        wf = wave.open(file_found, "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        rec.SetPartialWords(True)

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                print(rec.Result())
                asyncio.run(ctx.reply(rec.Result()))
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