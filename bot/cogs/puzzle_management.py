import datetime
import logging
from typing import List, Optional

import discord
from discord import app_commands
import pytz

from bot.base_cog import BaseCog, GeneralAppError
from bot.data.puzzle_db import PuzzleDb
from bot.utils import urls
from bot import database
from bot.database.models import PuzzleData, PuzzleNotes

logger = logging.getLogger(__name__)

class PuzzleManagement(BaseCog):
    PRIORITIES = ["low", "medium", "high", "very high"]

    def __init__(self, bot):
        self.bot = bot

    def clean_name(self, name):
        """Cleanup name to be appropriate for discord channel"""
        name = name.strip()
        if (name[0] == name[-1]) and name.startswith(("'", '"')):
            name = name[1:-1]
        return "-".join(name.lower().split())

    @app_commands.command()
    async def list_puzzles(self, interaction: discord.Interaction):
        """*List all puzzles and their statuses*"""
        if not (await self.check_is_bot_channel(interaction)):
            return

        all_puzzles = await PuzzleDb.get_all(interaction.guild.id)

        embed = discord.Embed()
        cur_round = None
        message = ""

        if len(all_puzzles) == 0:
            cur_round = ""
            message = "No puzzles to list"

        # Create a message with a new embed field per round,
        # listing all puzzles in the embed field
        for puzzle in all_puzzles:
            if cur_round is None:
                cur_round = puzzle.round_name
            if puzzle.round_name != cur_round or len(message) >= 512:
                # Reached next round, add new embed field
                embed.add_field(name=cur_round, value=message)
                cur_round = puzzle.round_name
                message = ""
            message += f"{puzzle.channel_mention}"
            if puzzle.puzzle_type:
                message += f" type:{puzzle.puzzle_type}"
            if puzzle.solution:
                message += f" sol:**{puzzle.solution}**"
            elif puzzle.status:
                message += f" status:{puzzle.status}"
            message += "\n"

        if len(message) > 0:
            # Add any dangling fields to our output
            embed.add_field(name=cur_round, value=message)

        if embed.fields:
            await interaction.response.send_message(embed=embed)

    async def send_not_puzzle_channel(self, interaction):
        await interaction.response.send_message("This does not appear to be a puzzle channel")

    @app_commands.command()
    async def set_round_url(self, interaction: discord.Interaction, round_url: str):
        guild = interaction.guild
        category = interaction.channel.category
        guild_settings = await database.query_guild(guild.id)
        round_settings = await database.query_round_data(guild.id, category.id)
        if guild_settings.discussion_channel == interaction.channel.name:
            if round_settings:
                await round_settings.update(round_url=round_url).apply()
                await interaction.response.send_message(f":white_check: Updated `round_url` to {round_url}")
            else:
                await interaction.response.send_message("Round not found")
        else:
            await interaction.response.send_message(f"Not in round discussion channel: {guild_settings.discussion_channel}")

    @app_commands.command()
    async def info(self, interaction: discord.Interaction):
        """*Show discord command help for a puzzle channel*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        settings = await database.query_guild(interaction.guild.id)
        channel_cog = self.bot.get_cog("ChannelManagement")
        if channel_cog is None:
            raise GeneralAppError("Unable to contact other cogs -- perhaps the server is misconfigured?")
        await interaction.response.send_message(embed=channel_cog.build_channel_info_message(settings.discussion_channel, interaction.channel))

    async def update_puzzle_attr_by_command(self, interaction: discord.Interaction,
                                            attr: str, value: Optional[str], message: Optional[str] = None,
                                            reply: bool =True) -> Optional[PuzzleData]:
        """Common pattern where we want to update a single field in PuzzleData based on command"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        if puzzle_data.is_solved():
            await interaction.response.send_message(
                 ":warning: Please note that this puzzle has already been marked as solved, "
                 f"with solution `{puzzle_data.solution}`"
            )

        message = message or attr
        if value:
            await puzzle_data.update(**{attr: value}).apply()
            message = "Updated! " + message

        if reply:
            embed = discord.Embed(description=f"""{message}: {getattr(puzzle_data, attr)}""")
            await interaction.response.send_message(embed=embed)
        return puzzle_data

    async def send_state(self, interaction: discord.Interaction, puzzle_data: PuzzleData, description=None):
        """Send simple embed showing relevant links"""
        embed = discord.Embed(description=description)
        embed.add_field(name="Hunt URL", value=puzzle_data.hunt_url or "?")
        spreadsheet_url = urls.spreadsheet_url(puzzle_data.google_sheet_id) if puzzle_data.google_sheet_id else "?"
        embed.add_field(name="Google Drive", value=spreadsheet_url)
        embed.add_field(name="Status", value=puzzle_data.status or "?")
        embed.add_field(name="Type", value=puzzle_data.puzzle_type or "?")
        embed.add_field(name="Priority", value=puzzle_data.priority or "?")
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def link(self, interaction: discord.Interaction, *, url: Optional[str]):
        """*Show or update link to puzzle*"""
        puzzle_data = await self.update_puzzle_attr_by_command(interaction, "hunt_url", url, reply=False)
        if puzzle_data:
            await self.send_state(
                interaction, puzzle_data, description=":white_check_mark: I've updated:" if url else None
            )

    @app_commands.command()
    async def sheet(self, interaction: discord.Interaction, *, url: Optional[str]):
        """*Show or update link to google spreadsheet for puzzle*"""
        file_id = None
        if url:
            file_id = urls.extract_id_from_url(url)
            if not file_id:
                interaction.response.send_message(f":exclamation: Invalid Google Drive URL, unable to extract file ID: {url}")

        puzzle_data = await self.update_puzzle_attr_by_command(interaction, "google_sheet_id", file_id, reply=False)
        if puzzle_data:
            await self.send_state(
                interaction, puzzle_data, description=":white_check_mark: I've updated:" if url else None
            )

    @app_commands.command()
    async def note(self, interaction: discord.Interaction, *, note: Optional[str]):
        """*Show or add a note about the puzzle*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        message = "Showing notes left by users!"

        notes = await puzzle_data.query_notes()

        if note:
             # TODO: get the jump_url for last message in channel?
             # Previously could use the command message itself, but with
             # slash command there is no longer a message.
             new_note = await puzzle_data.commit_note(note)
             message = (
                 f"Added a new note! Use `/erase_note {len(notes) + 1}` to remove the note if needed. "
                 f"Check `/note` for the current list of notes."
             )
             notes.append(new_note)
        await self._respond_show_notes(interaction, notes, message)

    async def _respond_show_notes(self, interaction: discord.Interaction, notes: List[PuzzleNotes], message: Optional[str]):
        """Respond to command by listing notes"""
        if notes:
            embed = discord.Embed(description=message)
            embed.add_field(
                name="Notes",
                value="\n".join([
                    # TODO: include jump_urls here once supported
                    f"{i+1}: {note_obj.text}" for i, note_obj in enumerate(notes)
                ])
            )
        else:
            embed = discord.Embed(description="No notes left yet, use `/note my note here` to leave a note")
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def erase_note(self, interaction: discord.Interaction, note_index: int):
        """*Remove a note by index*

        Warning:
            As this operates on the index of the note in the notes list
            of the puzzle, this is not safe wrt race conditions from
            multiple erase_note messages.
        """
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        # NOTE: This is very race un-safe: if two people try
        # to delete notes at the same time, the indices will
        # have changed by the time of the second delete, which
        # will cause a different note to get deleted.
        # As this is not a common operation, for now will just
        # leave as a unfortunate to-do.
        notes = await puzzle_data.query_notes()

        if 1 <= note_index <= len(notes):
            note = notes[note_index - 1]
            description = f"Erased note {note_index}: `{note.text}` - {note.jump_url}"
            await note.delete()
        else:
            description = f"Unable to find note {note_index}"

        notes = await puzzle_data.query_notes()
        await self._respond_show_notes(interaction, notes, description)

    @app_commands.command()
    async def status(self, interaction: discord.Interaction, *, status: Optional[str]):
        """*Show or update puzzle status, e.g. "extracting"*"""
        puzzle_data = await self.update_puzzle_attr_by_command(interaction, "status", status, reply=False)
        if puzzle_data:
            await self.send_state(
                interaction, puzzle_data, description=":white_check_mark: I've updated:" if status else None
            )

    @app_commands.command()
    async def type(self, interaction: discord.Interaction, *, puzzle_type: Optional[str]):
        """*Show or update puzzle type, e.g. "crossword"*"""
        puzzle_data = await self.update_puzzle_attr_by_command(interaction, "puzzle_type", puzzle_type, reply=False)
        if puzzle_data:
            await self.send_state(
                interaction, puzzle_data, description=":white_check_mark: I've updated:" if puzzle_type else None
            )

    @app_commands.command()
    async def priority(self, interaction: discord.Interaction, *, priority: Optional[str]):
        """*Show or update puzzle priority, one of "low", "medium", "high"*"""
        if priority is not None and priority not in self.PRIORITIES:
            await interaction.response.send_message(f":exclamation: Priority should be one of {self.PRIORITIES}, got \"{priority}\"")
            return

        puzzle_data = await self.update_puzzle_attr_by_command(interaction, "priority", priority, reply=False)
        if puzzle_data:
            await self.send_state(
                interaction, puzzle_data, description=":white_check_mark: I've updated:" if priority else None
            )

    @app_commands.command()
    async def solve(self, interaction: discord.Interaction, *, solution: str):
        """*Mark puzzle as fully solved, after confirmation from HQ*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        solution = solution.strip().upper()
        await puzzle_data.update(
            status = "solved",
            solution = solution,
            solve_time = datetime.datetime.now(tz=pytz.UTC)
        ).apply()

        settings = await database.query_guild(interaction.guild.id)
        emoji = settings.discord_bot_emoji
        embed = discord.Embed(
            description=f"{emoji} :partying_face: Great work! Marked the solution as `{solution}`"
        )
        delay = float(settings.archive_delay)/60
        delay_str = "%g minute" % delay
        if delay != 1.0:
            delay_str = delay_str + "s"
        embed.add_field(
            name="Follow-up",
            value="If the solution was mistakenly entered, please message `/unsolve`. "
            f"Otherwise, in around {delay_str}, I will automatically archive this "
            "puzzle channel to #solved-puzzles and archive the Google Spreadsheet",
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def unsolve(self, interaction: discord.Interaction):
        """*Mark an accidentally solved puzzle as not solved*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        prev_solution = puzzle_data.solution
        await puzzle_data.update(
            status = "unsolved",
            solution = "",
            solve_time = None
        ).apply()

        settings = await database.query_guild(interaction.guild.id)
        emoji = settings.discord_bot_emoji
        embed = discord.Embed(
            description=f"{emoji} Alright, I've unmarked {prev_solution} as the solution. "
            "You'll get'em next time!"
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PuzzleManagement(bot))

