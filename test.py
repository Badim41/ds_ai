import asyncio
import sys

import discord
from discord.ext import commands
from typing import Union
from discord import option, Option

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)

@bot.slash_command(name="channel")
@option(
    "channel",
    Union[discord.TextChannel, discord.VoiceChannel],
    # You can specify allowed channel types by passing a union of them like this.
    description="Select a channel",
)
async def select_channel(
    ctx: discord.ApplicationContext,
    channel: Union[discord.TextChannel, discord.VoiceChannel],
):
    await ctx.respond(f"Hi! You selected {channel.mention} channel.")

if __name__ == "__main__":
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))