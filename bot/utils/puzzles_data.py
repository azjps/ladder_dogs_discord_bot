from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
import datetime
import errno
import json
import logging
from pathlib import Path
from typing import List, Optional

import pytz

from bot.utils.puzzle_settings import DATA_DIR

logger = logging.getLogger(__name__)


class MissingPuzzleError(RuntimeError):
    pass


@dataclass_json
@dataclass
class PuzzleData:
    name: str
    round_name: str
    guild_id: int = 0
    guild_name: str = ""
    channel_id: int = ""
    channel_mention: str = ""
    # archive_channel_id: str = ""
    archive_channel_mention: str = ""
    hunt_url: str = ""
    google_sheet_id: str = ""
    google_folder_id: str = ""
    status: str = ""
    solution: str = ""
    priority: str = ""
    puzzle_type: str = ""
    notes: List[str] = field(default_factory=list)
    start_time: Optional[datetime.datetime] = None
    solve_time: Optional[datetime.datetime] = None
    archive_time: Optional[datetime.datetime] = None

    @classmethod
    def sort_by_round_start(cls, puzzles: list) -> list:
        """Return list of PuzzleData objects sorted by start of round time
        
        Groups puzzles in the same round together, and sorts puzzles within round
        by start_time.
        """
        round_start_times = {}

        for puzzle in puzzles:
            if puzzle.start_time is None:
                continue

            start_time = puzzle.start_time.timestamp()  # epoch time
            round_start_time = round_start_times.get(puzzle.round_name)
            if round_start_time is None or start_time < round_start_time:
                round_start_times[puzzle.round_name] = start_time

        return sorted(puzzles, key=lambda p: (round_start_times.get(p.round_name, 0), p.start_time or 0))


class _PuzzleJsonDb:
    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

    def puzzle_path(self, puzzle, round_name=None, guild_id=None) -> Path:
        if isinstance(puzzle, PuzzleData):
            puzzle_name = puzzle.name
            round_name = puzzle.round_name
            guild_id = puzzle.guild_id
        elif isinstance(puzzle, str):
            puzzle_name = puzzle
            if round_name is None or guild_id is None:
                raise ValueError(f"round_name / guild_id not passed for puzzle {puzzle}")
        else:
            raise ValueError(f"Unknown puzzle type: {type(puzzle)} for {puzzle}")
        return (self.dir_path / str(guild_id) / round_name / puzzle_name).with_suffix(".json")

    def commit(self, puzzle_data):
        puzzle_path = self.puzzle_path(puzzle_data)
        puzzle_path.parent.parent.mkdir(exist_ok=True)
        puzzle_path.parent.mkdir(exist_ok=True)
        with puzzle_path.open("w") as fp:
            fp.write(puzzle_data.to_json(indent=4))

    def delete(self, puzzle_data):
        puzzle_path = self.puzzle_path(puzzle_data)
        try:
            puzzle_path.unlink()
        except IOError:
            pass

    def get(self, guild_id, puzzle_name, round_name) -> PuzzleData:
        try:
            with self.puzzle_path(puzzle_name, round_name=round_name, guild_id=guild_id).open() as fp:
                return PuzzleData.from_json(fp.read())
        except (IOError, OSError) as exc:
            # can also just catch FileNotFoundError
            if exc.errno == errno.ENOENT:
                raise MissingPuzzleError(f"Unable to find puzzle {puzzle_name} for {round_name}")
            raise

    def get_all(self, guild_id) -> List[PuzzleData]:
        paths = self.dir_path.rglob(f"{guild_id}/*/*.json")
        puzzle_datas = []
        for path in paths:
            try:
                with path.open() as fp:
                    puzzle_datas.append(PuzzleData.from_json(fp.read()))
            except Exception:
                logger.exception(f"Unable to load puzzle data from {path}")
        return PuzzleData.sort_by_round_start(puzzle_datas)

    def get_solved_puzzles_to_archive(self, guild_id, now=None, include_meta=False) -> List[PuzzleData]:
        all_puzzles = self.get_all(guild_id)
        now = now or datetime.datetime.now(tz=pytz.UTC)
        puzzles_to_archive = []
        for puzzle in all_puzzles:
            if puzzle.archive_time is not None:
                # already archived
                continue
            if puzzle.name == "meta" and not include_meta:
                # we usually do not want to archive meta channels, only do manually
                continue
            if puzzle.status == "solved" and puzzle.solve_time is not None:
                # found a solved puzzle
                if now - puzzle.solve_time > datetime.timedelta(minutes=5):
                    # enough time has passed, archive the channel
                    puzzles_to_archive.append(puzzle)
        return puzzles_to_archive

    def aggregate_json(self) -> dict:
        paths = self.dir_path.rglob(f"*/*.json")
        result = {}
        for path in paths:
            relpath = path.relative_to(self.dir_path)
            with path.open() as fp:
                result[str(relpath)] = json.load(fp)
        return result

PuzzleJsonDb = _PuzzleJsonDb(dir_path=DATA_DIR)