import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.base_cog import BaseCog
from bot import database
from bot.database.models import HuntSettings

logger = logging.getLogger(__name__)


class HuntManagement(BaseCog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_hunt_settings_from_channel(
        self, interaction: discord.Interaction
    ) -> Optional[HuntSettings]:
        guild_id = interaction.guild.id
        guild_settings = await database.query_guild(guild_id)
        if interaction.channel.name == guild_settings.discord_bot_channel:
            active_hunts = await HuntSettings.get_active_hunts(guild_id)
            if len(active_hunts) == 1:
                settings = active_hunts[0]
            else:
                hunt_names = [hunt.hunt_name for hunt in active_hunts]
                await interaction.response.send_message(
                    f"# of active hunts != 1: {len(active_hunts)} {hunt_names}."
                )
                return
        else:
            settings = await database.query_hunt_settings_by_round(
                guild_id, interaction.channel.category.id
            )
        return settings

    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def show_hunt_settings(self, interaction: discord.Interaction):
        """*(admin) Show guild-level settings*"""
        settings = await self._get_hunt_settings_from_channel(interaction)
        if not settings:
            return
        await interaction.response.send_message(f"```json\n{settings.to_json()}```")

    # TODO: use choices for setting_key:
    # https://stackoverflow.com/questions/72043793/discord-py-how-to-create-choice-with-slash-command
    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def update_hunt_setting(
        self, interaction: discord.Interaction, setting_key: str, setting_value: str
    ):
        """*(admin) Update hunt setting: /update_hunt_setting key value*"""
        settings = await self._get_hunt_settings_from_channel(interaction)
        if not settings:
            return
        if hasattr(settings, setting_key):
            old_value = getattr(settings, setting_key)
            await settings.set({setting_key: setting_value})
            await interaction.response.send_message(
                f":white_check_mark: Updated `{setting_key}={setting_value}` from old value: `{old_value}`"
            )
        else:
            await interaction.response.send_message(
                f":exclamation: Unrecognized setting key: `{setting_key}`. Use `/show_hunt_settings` for more info."
            )

    @app_commands.command()
    async def hunt_end(
        self, interaction: discord.Interaction, *, hunt_name: str, is_ended: bool = True
    ):
        """End the hunt. Note that puzzle channel creation etc may no longer work afterwards"""
        if await self._error_if_not_bot_channel(interaction, "hunt_end"):
            return

        settings = await database.query_hunt_settings_by_name(
            interaction.guild.id, hunt_name, allow_create=False
        )
        if is_ended:
            await settings.update(end_time=datetime.datetime.now(tz=pytz.UTC)).apply()
            await interaction.response.send_message(f"Have ended hunt: {hunt_name}. Congrats!")
        else:
            await settings.update(end_time=None).apply()
            await interaction.response.send_message(f"Have un-ended hunt: {hunt_name}")



async def setup(bot):
    await bot.add_cog(HuntManagement(bot))
