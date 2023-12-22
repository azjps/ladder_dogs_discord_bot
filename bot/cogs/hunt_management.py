import logging

import discord
from discord import app_commands
from discord.ext import commands 

from bot.splat_store_cog import SplatStoreCog
from bot import database
from bot.database.models import HuntSettings 

logger = logging.getLogger(__name__)

class HuntManagement(SplatStoreCog):

    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def show_hunt_settings(self, interaction: discord.Interaction):
        """*(admin) Show guild-level settings*"""
        guild_id = interaction.guild.id
        settings = await database.query_hunt_settings_by_round(guild_id, interaction.channel.category.id)
        await interaction.response.send_message(f"```json\n{settings.to_json()}```")

    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def update_hunt_setting(self, interaction: discord.Interaction, setting_key: str, setting_value: str):
        """*(admin) Update guild setting: /update_setting key value*"""
        guild_id = interaction.guild.id
        settings = await database.query_hunt_settings_by_round(guild_id, interaction.channel.category.id)
        if hasattr(settings, setting_key):
            old_value = getattr(settings, setting_key)
            await settings.set({setting_key: setting_value})
            await interaction.response.send_message(f":white_check_mark: Updated `{setting_key}={setting_value}` from old value: `{old_value}`")
        else:
            await interaction.response.send_message(f":exclamation: Unrecognized setting key: `{setting_key}`. Use `/show_settings` for more info.")

async def setup(bot):
    await bot.add_cog(HuntManagement(bot))

