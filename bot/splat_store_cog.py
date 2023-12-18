import logging
from typing import List, Optional

import discord
from discord.ext import commands 

from bot import database
from bot.database.models import HuntSettings, PuzzleData
from bot.data.puzzle_db import MissingPuzzleError, PuzzleDb

logger = logging.getLogger(__name__)

"""
Base cog class which holds some common code for all of the cogs in this application.
"""
class SplatStoreCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{type(self).__name__} Cog ready.")

    async def cog_app_command_error(self, interaction, error):
        logger.exception(error)
        if interaction.response.is_done():
            await interaction.response.edit_message(":exclamation: " + str(error))
        else:
            await interaction.response.send_message(":exclamation: " + str(error))

    async def check_is_bot_channel(self, interaction) -> bool:
        """Check if command was sent to bot channel configured in settings"""
        settings = await database.query_hunt_settings(interaction.guild.id)
        if not settings.discord_bot_channel:
            # If no channel is designated, then all channels are fine
            # to listen to commands.
            return True

        if interaction.channel.name == settings.discord_bot_channel:
            # Channel name matches setting (note, channel name might not be unique)
            return True

        await interaction.response.send_message(f":exclamation: Most bot commands should be sent to #{settings.discord_bot_channel}")
        return False

    async def get_puzzle_data_from_channel(self, channel) -> Optional[PuzzleData]:
        """Extract puzzle data based on the channel name and category name

        Looks up the corresponding JSON data
        """
        if not channel.category:
            return None

        guild = channel.guild
        guild_id = guild.id
        round_id = channel.category.id
        round_name = channel.category.name
        puzzle_id = channel.id
        puzzle_name = channel.name
        try:
            return await PuzzleDb.get(guild_id, puzzle_id)
        except MissingPuzzleError:
            # Not the cleanest, just try to guess the original category id
            # A DB would be useful here, then can directly query on solved_channel_id ..
            logger.error(f"Unable to retrieve puzzle={puzzle_id} round={round_id} {round_name}/{puzzle_name}")
            return None


class GeneralAppError(RuntimeError):
    pass
