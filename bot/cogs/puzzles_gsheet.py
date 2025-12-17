"""
Google Drive integration for puzzle organization

This is a separate cog so that Google Drive integration
can be easily disabled; simply omit this file.
"""

import datetime
import logging
import string
import pytz

import discord
from discord.ext import tasks
import gspread_asyncio
import gspread_formatting

from bot.base_cog import BaseCog
from bot.utils import urls
from bot.utils.gdrive import get_or_create_folder, rename_file
from bot.utils.gsheet import copy_spreadsheet, create_spreadsheet, get_manager
from bot.utils.gsheet_nexus import update_nexus
from bot import database
from bot.database.models import GuildSettings, HuntSettings, PuzzleData, RoundData

logger = logging.getLogger(__name__)


class GoogleSheets(BaseCog):
    agcm = get_manager()

    def __init__(self, bot):
        self.stale_hunt_days = 90
        self.bot = bot

    def begin_loops(self):
        logger.info("Beginning loops")
        self.refresh_nexus.start()
        self.refresh_stale_nexus.start()

    def cap_name(self, name):
        """Capitalize name for easy comprehension"""
        return string.capwords(name.replace("-", " "))

    async def create_puzzle_spreadsheet(
        self, text_channel: discord.TextChannel, puzzle: PuzzleData
    ):
        guild_id = text_channel.guild.id
        name = self.cap_name(puzzle.name)
        round_name = self.cap_name(puzzle.round_name)
        if name == "meta":
            # Distinguish metas between different rounds
            name = f"{name} ({round_name})"

        hunt_settings = await database.query_hunt_settings_by_round(guild_id, puzzle.round_id)
        if not hunt_settings.drive_hunt_folder_id:
            return

        try:
            # default to storing everything in with the hunt
            round_folder_id = hunt_settings.drive_hunt_folder_id

            # create drive folder if needed.  If the round is the same name as the hunt, just keep it at the top level.
            if hunt_settings.hunt_name != puzzle.round_name:
                round_folder = await get_or_create_folder(
                    name=round_name, parent_id=hunt_settings.drive_hunt_folder_id
                )
                round_folder_id = round_folder["id"]

            guild_settings = await database.query_guild(guild_id)
            if guild_settings.drive_starter_sheet_id:
                spreadsheet = await copy_spreadsheet(
                    agcm=self.agcm,
                    source_id=guild_settings.drive_starter_sheet_id,
                    title=name,
                    folder_id=round_folder_id,
                )
            else:
                spreadsheet = await create_spreadsheet(
                    agcm=self.agcm, title=name, folder_id=round_folder_id
                )
            await puzzle.update(
                google_folder_id=round_folder_id, google_sheet_id=spreadsheet.id
            ).apply()

            # inform spreadsheet creation
            puzzle_url = puzzle.hunt_url
            sheet_url = urls.spreadsheet_url(spreadsheet.id)
            emoji = guild_settings.discord_bot_emoji
            embed = discord.Embed(
                description=f"{emoji} I've created a spreadsheet for you at {sheet_url}. "
                f"Check out the `Quick Links` tab for more info! "
                # NOTE: This next sentence might be better elsewhere, for now easy enough to add message here.
                f"I've assumed the puzzle page is {puzzle_url}, use `/link` to update if needed."
            )
            
            # Check if we should edit the first message instead of sending a new one
            if guild_settings.sticky_first_message:
                # Get the first message in the channel to edit it instead of sending a new message
                async for message in text_channel.history(limit=1):
                    if message.author == self.bot.user:
                        # Edit the first bot message instead of sending a new one
                        # Append the new embed content after the existing message text
                        new_content = message.embeds[0]
                        new_content.add_field(name="Spreadsheet", value=embed.description)
                        await message.edit(embed=new_content)
                        await message.pin()
                        break
                else:
                    # If no bot message found, send a new message (fallback)
                    await text_channel.send(embed=embed)
            else:
                # Default behavior - send a new message
                await text_channel.send(embed=embed)

            # add some helpful links
            await self.add_quick_links_worksheet(spreadsheet, puzzle, guild_settings, hunt_settings)

        except Exception as exc:
            logger.exception(f"Unable to create spreadsheet for {round_name}/{name}")
            await text_channel.send(
                f":exclamation: Unable to create spreadsheet for {round_name}/{name}: {exc}"
            )
            return

        return spreadsheet

    async def create_hunt_drive(
        self, guild_id: int, text_channel: discord.TextChannel, hunt: HuntSettings
    ):
        settings = await database.query_guild(guild_id)
        if settings.drive_parent_id is None:
            logger.info(
                f"Setting 'drive_parent_id' not set for this guild, skipping drive integration for new hunt {hunt.hunt_name}"
            )
            return
        folder = await get_or_create_folder(self.cap_name(hunt.hunt_name), settings.drive_parent_id)
        await hunt.update(drive_hunt_folder_id=folder["id"]).apply()
        await self.create_hunt_nexus_sheet(guild_id, text_channel, hunt)

    async def create_hunt_nexus_sheet(
        self, guild_id: int, text_channel: discord.TextChannel, hunt: HuntSettings
    ):
        if not hunt.drive_hunt_folder_id:
            return

        if hunt.drive_nexus_sheet_id is not None:
            sheet_url = urls.spreadsheet_url(hunt.drive_nexus_sheet_id)
            await text_channel.send(
                f":exclamation: Previously created spreadsheet for {hunt.hunt_name}: {sheet_url}"
            )
            return

        try:
            spreadsheet = await create_spreadsheet(
                agcm=self.agcm, title="Nexus", folder_id=hunt.drive_hunt_folder_id
            )
            await hunt.update(drive_nexus_sheet_id=spreadsheet.id).apply()

            # inform spreadsheet creation
            sheet_url = urls.spreadsheet_url(spreadsheet.id)
            guild_settings = await database.query_guild(guild_id)
            emoji = guild_settings.discord_bot_emoji
            embed = discord.Embed(
                description=f"{emoji} I've created a drive nexus spreadsheet for you at {sheet_url}. "
            )
            await text_channel.send(embed=embed)
        except Exception as exc:
            logger.exception(f"Unable to create nexus spreadsheet for {hunt.hunt_name}")
            await text_channel.send(
                f":exclamation: Unable to create nexus spreadsheet for {hunt.hunt_name}: {exc}"
            )
            return

        return spreadsheet

    def update_cell_row(self, cell_range, row: int, key: str, value: str):
        """Update key-value row cell contents; row starts from 1"""
        cell_range[(row - 1) * 2].value = key
        cell_range[(row - 1) * 2 + 1].value = value

    async def add_quick_links_worksheet(
        self,
        spreadsheet: gspread_asyncio.AsyncioGspreadSpreadsheet,
        puzzle: PuzzleData,
        guild_settings: GuildSettings,
        hunt_settings: HuntSettings,
    ):
        worksheet = await spreadsheet.add_worksheet(title="Quick Links", rows=10, cols=2)
        cell_range = await worksheet.range(1, 1, 10, 2)

        self.update_cell_row(cell_range, 1, "Hunt URL", puzzle.hunt_url)
        self.update_cell_row(
            cell_range,
            2,
            "Drive folder",
            urls.drive_folder_url(puzzle.google_folder_id),
        )
        nexus_url = (
            urls.spreadsheet_url(hunt_settings.drive_nexus_sheet_id)
            if hunt_settings.drive_nexus_sheet_id
            else ""
        )
        self.update_cell_row(cell_range, 3, "Nexus", nexus_url)
        resources_url = (
            urls.docs_url(hunt_settings.drive_resources_id)
            if hunt_settings.drive_resources_id
            else (
                urls.docs_url(guild_settings.drive_resources_id)
                if guild_settings.drive_resources_id
                else ""
            )
        )
        self.update_cell_row(cell_range, 4, "Resources", resources_url)
        self.update_cell_row(cell_range, 5, "Discord channel mention", puzzle.channel_mention)
        self.update_cell_row(
            cell_range,
            6,
            "Reminders",
            "Please create a new worksheet if you're making large changes (e.g. re-sorting)",
        )
        self.update_cell_row(
            cell_range, 7, "", "You can use Ctrl+Alt+M to leave a comment on a cell"
        )
        await worksheet.update_cells(cell_range)

        # Not async
        gspread_formatting.set_column_width(worksheet.ws, "B", 1000)

    async def archive_puzzle_spreadsheet(self, puzzle: PuzzleData) -> dict:
        def archive_puzzle_name(sheet_name):
            if "SOLVED" in sheet_name:
                return sheet_name
            return f"[SOLVED: {puzzle.solution}] {sheet_name}"

        if puzzle.google_sheet_id is None:
            return None
        return await rename_file(puzzle.google_sheet_id, name_lambda=archive_puzzle_name)

    @tasks.loop(hours=24)
    async def refresh_stale_nexus(self):
        # This loop will run every 24 hours and updates hunts that ended a long time ago. (stale_hunt_days ago)
        hunts = await HuntSettings.query.gino.all()
        now = datetime.datetime.now(tz=pytz.UTC)
        for hunt in hunts:
            if self.hunt_is_stale(hunt, now):
                await self.update_nexus_sheet(hunt)

    @tasks.loop(seconds=60.0)
    async def refresh_nexus(self):
        """Ref: https://discordpy.readthedocs.io/en/latest/ext/tasks/"""
        hunts = await HuntSettings.query.gino.all()
        now = datetime.datetime.now(tz=pytz.UTC)
        for hunt in hunts:
            if not self.hunt_is_stale(hunt, now):
                await self.update_nexus_sheet(hunt)

    @refresh_nexus.before_loop
    async def before_refreshing_nexus(self):
        await self.bot.wait_until_ready()
        logger.info("Ready to start updating nexus spreadsheet")

    async def update_nexus_sheet(self, hunt):
        if hunt.drive_nexus_sheet_id:
            rounds = await RoundData.rounds_in_hunt(hunt)
            puzzles = []
            for round_data in rounds:
                puzzles.extend(await PuzzleData.puzzles_in_round(round_data.category_id))
            if puzzles:
                await update_nexus(
                    agcm=self.agcm,
                    file_id=hunt.drive_nexus_sheet_id,
                    puzzles=puzzles,
                    hunt_name=hunt.hunt_name,
                )

    def hunt_is_stale(self, hunt, now=None):
        """Returns True if the hunt is stale, False otherwise."""
        if now is None:
            now = datetime.datetime.now(tz=pytz.UTC)
        return hunt.end_time and now - hunt.end_time > datetime.timedelta(days=self.stale_hunt_days)


async def setup(bot):
    # Comment this out if google-drive-related package are not installed!
    await bot.add_cog(GoogleSheets(bot))
