from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import datetime
import errno
import json
import logging
from pathlib import Path
from typing import List, Optional

import pytz
from bot import database
from bot.database.models import PuzzleData


logger = logging.getLogger(__name__)

class MissingPuzzleError(RuntimeError):
    pass

class PuzzleDb:

    @classmethod
    async def delete(cls, puzzle_data):
        await puzzle_data.update(delete_time = datetime.datetime.now(tz=pytz.UTC)).apply()

    @classmethod
    async def get(cls, guild_id, puzzle_id) -> PuzzleData:
        puzzle = await PuzzleData.query.where(
            (PuzzleData.guild_id == guild_id) &
			(PuzzleData.channel_id == puzzle_id)
		).gino.first()
        if puzzle is None:
            raise MissingPuzzleError(f"Unable to find puzzle {puzzle_id} for {round_id}")
        return puzzle

    @classmethod
    async def get_all(cls, guild_id) -> List[PuzzleData]:
        puzzle_datas = await PuzzleData.query.where(
            (PuzzleData.guild_id == guild_id) 
		).gino.all()
        return PuzzleData.sort_by_round_start(puzzle_datas)

    @classmethod
    async def get_solved_puzzles_to_archive(cls, guild_id, now=None, include_general: bool = False, minutes: Optional[int] = 5) -> List[PuzzleData]:
        """Returns list of all solved but unarchived puzzles"""
        all_puzzles = await cls.get_all(guild_id)
        now = now or datetime.datetime.now(tz=pytz.UTC)
        puzzles_to_archive = []
        settings = await database.query_hunt_settings(guild_id)
        for puzzle in all_puzzles:
            if puzzle.archive_time is not None:
                # already archived
                continue
            if puzzle.name == settings.discussion_channel and not include_general:
                # we usually do not want to archive general channels, only do manually
                continue
            if puzzle.is_solved():
                # found a solved puzzle
                if minutes is None:
                    minutes = 5  # default to archiving puzzles that have been solved for 5 minutes. Un-hard-code?
                if now - puzzle.solve_time > datetime.timedelta(minutes=minutes):
                    # enough time has passed, archive the channel
                    puzzles_to_archive.append(puzzle)
        return puzzles_to_archive

    @classmethod
    async def get_puzzles_to_delete(cls, guild_id: int, include_general: bool = False, minutes: int = 5) -> List[PuzzleData]:
        """Return list of puzzles to delete"""
        all_puzzles = await cls.get_all(guild_id)
        now = datetime.datetime.now(tz=pytz.UTC)
        puzzles_to_delete = []
        settings = await database.query_hunt_settings(guild_id)
        for puzzle in all_puzzles:
            if puzzle.solve_time is not None or puzzle.archive_time is not None:
                # already archived
                continue
            if puzzle.name == settings.discussion_channel and not include_general:
                # we usually do not want to archive general channels, only do manually
                continue
            if puzzle.delete_time is not None:
                # found a puzzle to delete
                if minutes is None:
                    minutes = 5  # default to archiving puzzles that have been solved for 5 minutes. Un-hard-code?
                if now - puzzle.delete_time > datetime.timedelta(minutes=minutes):
                    # enough time has passed, archive the channel
                    puzzles_to_delete.append(puzzle)
        return puzzles_to_delete

