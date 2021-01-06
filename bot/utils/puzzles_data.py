from dataclasses import dataclass
from dataclasses_json import dataclass_json
import datetime
import errno
import json
from pathlib import Path
from typing import Optional

import pytz

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
    archive_channel_id: str = ""
    archive_channel_mention: str = ""
    hunt_url: str = ""
    google_docs_url: str = ""
    status: str = ""
    solution: str = ""
    puzzle_type: str = ""
    start_time: Optional[datetime.datetime] = None
    solve_time: Optional[datetime.datetime] = None
    archive_time: Optional[datetime.datetime] = None


class _PuzzleJsonDb:
    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

    def puzzle_path(self, puzzle, round_name=None) -> Path:
        if isinstance(puzzle, PuzzleData):
            puzzle_name = puzzle.name
            round_name = puzzle.round_name
        elif isinstance(puzzle, str):
            puzzle_name = puzzle
            if round_name is None:
                raise ValueError(f"round_name not passed for puzzle {puzzle}")
        else:
            raise ValueError(f"Unknown puzzle type: {type(puzzle)} for {puzzle}")
        return (self.dir_path / round_name / puzzle_name).with_suffix(".json")

    def commit(self, puzzle_data):
        puzzle_path = self.puzzle_path(puzzle_data)
        puzzle_path.parent.mkdir(exist_ok=True)
        with puzzle_path.open("w") as fp:
            fp.write(puzzle_data.to_json(indent=4))

    def delete(self, puzzle_data):
        puzzle_path = self.puzzle_path(puzzle_data)
        try:
            puzzle_path.unlink()
        except IOError:
            pass

    def get(self, puzzle_name, round_name) -> PuzzleData:
        try:
            with self.puzzle_path(puzzle_name, round_name=round_name).open() as fp:
                return PuzzleData.from_json(fp.read())
        except IOError as exc:
            if exc.errno == errno.EEXIST:
                raise MissingPuzzleError(f"Unable to find puzzle {puzzle_name} for {round_name}")
            raise

    def get_all(self) -> list[PuzzleData]:
        paths = self.dir_path.rglob("*/*.json")
        puzzle_datas = []
        for path in paths:
            try:
                with path.open() as fp:
                    puzzle_datas.append(PuzzleData.from_json(fp.read()))
            except Exception as exc:
                # TODO(azhu): use logging
                print(f"Unable to load puzzle data from {path}: {exc}")
        return puzzle_datas

    def get_solved_puzzles_to_archive(self, now=None) -> list[PuzzleData]:
        all_puzzles = self.get_all()
        now = now or datetime.datetime.now(tz=pytz.UTC)
        puzzles_to_archive = []
        for puzzle in all_puzzles:
            if puzzle.archive_time is not None:
                # already archived
                continue
            if puzzle.status == "solved" and puzzle.solve_time is not None:
                # found a solved puzzle
                if now - puzzle.solve_time > datetime.timedelta(minutes=5):
                    # enough time has passed, archive the channel
                    puzzles_to_archive.append(puzzle)
        return puzzles_to_archive
        

PuzzleJsonDb = _PuzzleJsonDb(dir_path=Path(__file__).parent.parent.parent / "data")