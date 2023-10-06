import asyncio
import multiprocessing

import discord
from discord.ext import commands
from test2 import StreamSink
import sys
import configparser
import vosk
from vosk import Model
config = configparser.ConfigParser()
config.read('config.ini')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

connections = {}

stream_sink = StreamSink()


async def is_record(value=None):
    if value is None:
        config.read('config.ini')
        return config.getboolean("Sound", "record")
    config.read('config.ini')
    config.set('Sound', "record", value)
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
    pool = multiprocessing.Pool(processes=1)
    pool.apply_async(recognize)
    pool.close()
    await ctx.reply("Started listening.")


# our voice client already passes these in.
async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await is_record(value=False)
    await sink.vc.disconnect()  # disconnect from the voice channel.
    print("Stopped listening.")

def recognize():
    while asyncio.run(is_record()):
        model = Model(lang="en-us")
        rec = vosk.KaldiRecognizer(model, 16000)
        rec.SetWords(True)
        rec.SetPartialWords(True)
        while True:
            data = stream_sink.buffer
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                spokenText = rec.Result()
                spokenText = spokenText[spokenText.find(":") + 3:spokenText.find("\"", spokenText.find(":") + 3)]
                if spokenText:
                    print(spokenText)
                    pass
            else:
                print(rec.PartialResult())
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
    print("update 1")
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
    else:
        print("Укажите discord_TOKEN")
        exit(-1)
    bot.run(discord_token)