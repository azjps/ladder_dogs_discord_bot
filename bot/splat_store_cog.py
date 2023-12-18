import logging

import discord
from discord.ext import commands 

from bot import database
from bot.database.models import HuntSettings 

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

