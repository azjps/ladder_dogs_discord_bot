import sys
import time
from datetime import datetime
import logging

import discord
from discord import app_commands

from bot.splat_store_cog import SplatStoreCog

PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

logger = logging.getLogger(__name__)

class Utility(SplatStoreCog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now().replace(microsecond=0)

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        """*Current ping and latency of the bot*
        **Example**: `/ping`"""
        embed = discord.Embed()
        before_time = time.time()
        latency = round(self.bot.latency * 1000)
        elapsed_ms = round((time.time() - before_time) * 1000) - latency
        embed.add_field(name="ping", value=f"{elapsed_ms}ms")
        embed.add_field(name="latency", value=f"{latency}ms")
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def uptime(self, interaction: discord.Interaction):
        """*Current uptime of the bot*
        **Example**: `/uptime`"""
        current_time = datetime.now().replace(microsecond=0)
        await interaction.response.send_message(f"Time since I went online: {current_time - self.start_time}.")

    @app_commands.command()
    async def starttime(self, interaction: discord.Interaction):
        """*When the bot was started*
        **Example**: `/starttime`"""
        embed = discord.Embed(description=f"I'm up since {self.start_time}.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def info_bot(self, interaction: discord.Interaction):
        """*Shows stats and infos about the bot*
        **Example**: `/info_bot`"""
        embed = discord.Embed(title="LadderSpot")
        # embed.url = f"https://top.gg/bot/{self.bot.user.id}"
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(
            name="Bot Stats",
            value=f"```py\n"
            f"Guilds: {len(self.bot.guilds)}\n"
            f"Users: {len(self.bot.users)}\n"
            f"Shards: {self.bot.shard_count}\n"
            f"Shard ID: {interaction.guild.shard_id}```",
            inline=False,
        )
        embed.add_field(
            name="Software Versions",
            value=f"```py\n"
            f"LadderSpot: {self.bot.version}\n"
            f"discord.py: {discord.__version__}\n"
            f"Python: {PY_VERSION}```",
            inline=False,
        )
        embed.add_field(
            name="Links",
            value=f"[Invite]({self.bot.invite})",
            inline=False,
        )
        embed.set_footer(text=":ladder: :dog:", icon_url=self.bot.user.avatar_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def invite(self, interaction: discord.Interaction):
        """*Shows invite link and other socials for the bot*
        **Example**: `/invite`"""
        embed = discord.Embed()
        embed.description = f"[Invite]({self.bot.invite})"
        embed.set_footer(text=":ladder: :dog:", icon_url=self.bot.user.avatar_url)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
