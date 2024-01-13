import asyncio
import sys

import discord
from discord.ext import commands
from typing import Union
from discord import option, Option

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)

@bot.slash_command(name='test_slash_command', description='Отвечает "Успешный тест!"')
async def __test(ctx):
    await ctx.respond('Успешный тест!')

@bot.slash_command(name='test_del_command', description='Удаляет контекст и выводит сообщение "Успешный тест!"')
async def __test(ctx):
    await ctx.delete()
    await ctx.send('Успешный тест!')

if __name__ == "__main__":
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))