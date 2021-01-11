import datetime
import logging
import string
from typing import Optional

import discord
from discord.ext import commands
import gspread_asyncio
import gspread_formatting
import pytz

from bot.utils import urls
from bot.utils.puzzles_data import MissingPuzzleError, PuzzleData, PuzzleJsonDb
from bot.utils.puzzle_settings import GuildSettingsDb
from bot.utils.gdrive import get_or_create_folder, rename_file
from bot.utils.gsheet import create_spreadsheet, get_manager

logger = logging.getLogger(__name__)


class GoogleSheets(commands.Cog):
    agcm = get_manager()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{type(self).__name__} Cog ready.")

    def cap_name(self, name):
        """Capitalize name for easy comprehension"""
        return string.capwords(name.replace("-", " "))

    async def create_puzzle_spreadsheet(self, text_channel: discord.TextChannel, puzzle: PuzzleData):
        guild_id = text_channel.guild.id
        name = puzzle.name
        round_name = puzzle.round_name
        settings = GuildSettingsDb.get(guild_id)
        if not settings.drive_parent_id:
            return

        try:
            # create drive folder if needed
            round_folder = await get_or_create_folder(
                name=self.cap_name(round_name), parent_id=settings.drive_parent_id
            )
            round_folder_id = round_folder["id"]

            spreadsheet = await create_spreadsheet(agcm=self.agcm, title=self.cap_name(name), folder_id=round_folder_id)
            puzzle.google_folder_id = round_folder_id
            puzzle.google_sheet_id = spreadsheet.id
            PuzzleJsonDb.commit(puzzle)

            # inform spreadsheet creation
            url = urls.spreadsheet_url(spreadsheet.id)
            embed = discord.Embed(
                description=f":ladder: :dog: I've created a spreadsheet for you at {url} Check out the `Quick Links` tab for more info!"
            )
            await text_channel.send(embed=embed)

            # add some helpful links
            await self.add_quick_links_worksheet(spreadsheet, puzzle)

        except Exception as exc:
            logger.exception(f"Unable to create spreadsheet for {round_name}/{name}")
            await text_channel.send(f":exclamation: Unable to create spreadsheet for {round_name}/{name}: {exc}")
            return

        return spreadsheet

    def update_cell_row(self, cell_range, row: int, key: str, value: str):
        """Update key-value row cell contents; row starts from 1"""
        cell_range[(row - 1) * 2].value = key
        cell_range[(row - 1) * 2 + 1].value = value

    async def add_quick_links_worksheet(
        self, spreadsheet: gspread_asyncio.AsyncioGspreadSpreadsheet, puzzle: PuzzleData
    ):
        worksheet = await spreadsheet.add_worksheet(title="Quick Links", rows=10, cols=2)
        cell_range = await worksheet.range(1, 1, 10, 2)

        self.update_cell_row(cell_range, 1, "Hunt URL", puzzle.hunt_url)
        self.update_cell_row(cell_range, 2, "Drive folder", urls.drive_folder_url(puzzle.google_folder_id))
        self.update_cell_row(cell_range, 3, "Discord channel mention", puzzle.channel_mention)
        self.update_cell_row(
            cell_range, 4, "Reminders", "Please create a new worksheet if you're making large changes (e.g. re-sorting)"
        )
        self.update_cell_row(cell_range, 5, "", "You can use Ctrl+Alt+M to leave a comment on a cell")
        await worksheet.update_cells(cell_range)

        # Not async
        gspread_formatting.set_column_width(worksheet.ws, "B", 1000)

    async def archive_puzzle_spreadsheet(self, puzzle: PuzzleData) -> dict:
        def archive_puzzle_name(sheet_name):
            if "SOLVED" in sheet_name:
                return sheet_name
            return f"[SOLVED: {puzzle.solution}] {sheet_name}"

        return await rename_file(puzzle.google_sheet_id, name_lambda=archive_puzzle_name)


def setup(bot):
    # Comment this out if google-drive-related package are not installed!
    bot.add_cog(GoogleSheets(bot))

