import datetime
import logging
import string
from typing import Optional

import discord
from discord.ext import commands
import pytz

from bot.utils.puzzles_data import MissingPuzzleError, PuzzleData, PuzzleJsonDb
from bot.utils.puzzle_settings import GuildSettingsDb
from bot.utils.gdrive import get_or_create_folder
from bot.utils.gsheet import create_spreadsheet, get_manager, spreadsheet_link

logger = logging.getLogger(__name__)
agcm = get_manager()

class GoogleSheets(commands.Cog):
    def cap_name(self, name):
        """Capitalize name for easy comprehension"""
        return string.capwords(name.replace("-", " "))

    async def create_puzzle_spreadsheet(self, text_channel: discord.TextChannel, name: str, round_name: str):
        guild_id = text_channel.guild.id
        settings = GuildSettingsDb.get(guild_id)
        if not settings.drive_parent_id:
            return

        try:
            round_folder = await get_or_create_folder(name=self.cap_name(round_name), parent_id=settings.drive_parent_id)
            round_folder_id = round_folder["id"]

            agclient = agcm.authorize()
            spreadsheet = await create_spreadsheet(agc=agclient, title=self.cap_name(name), folder_id=round_folder_id)
        except Exception as exc:
            text_channel.send(f"Unable to create spreadsheet for {round_name}/{name}: {exc}")
            return

        url = spreadsheet_link(spreadsheet.id)
        text_channel.send(f"I've created a spreadsheet for you at {url}")
        return spreadsheet


def setup(bot):
    # Comment this out if google-drive-related package are not installed!
    bot.add_cog(GoogleSheets(bot))

