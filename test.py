import asyncio
import sys

import nextcord
from nextcord import Interaction, SlashOption
from nextcord.ext import commands

bot = commands.Bot()


@bot.slash_command()
async def choose_a_number(
    interaction: Interaction,
    number: int = SlashOption(
        name="picker",
        description="The number you want",
        choices={"one": 1, "two": 2, "three": 3},
    ),
):
    await interaction.response.send_message(f"You chose {number}!")


@bot.slash_command()
async def hi(
    interaction: Interaction,
    member: nextcord.Member = SlashOption(name="user", description="User to say hi to"),
):
    await interaction.response.send_message(f"{interaction.user} just said hi to {member.mention}")

if __name__ == "__main__":
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))