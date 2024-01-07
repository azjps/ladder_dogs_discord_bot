import datetime
from typing import Optional

import pytz

from bot.database import db


class PuzzleData(db.Model):
    __tablename__ = "puzzle_data"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)

    # NOTE: round_id is being set to the discord category UID, and not
    # the PK of the round_data table.
    round_id = db.Column(db.BIGINT,
                         db.ForeignKey("round_data.category_id",
                                       onupdate="CASCADE", ondelete="CASCADE"),
                         default=0)

    ### These should just be pulled from relationship to round:
    round_name = db.Column(db.Text)
    solved_round_id = db.Column(db.BIGINT, default=0)
    guild_id = db.Column(db.BIGINT, default=0)
    guild_name = db.Column(db.Text)
    ###

    channel_id = db.Column(db.BIGINT, default=0)
    channel_mention = db.Column(db.Text)
    voice_channel_id = db.Column(db.BIGINT, default=0)
    archive_channel_mention = db.Column(db.Text)
    hunt_url = db.Column(db.Text)
    google_sheet_id = db.Column(db.Text)
    google_folder_id = db.Column(db.Text)
    status = db.Column(db.Text)
    solution = db.Column(db.Text)
    priority = db.Column(db.Text)
    puzzle_type = db.Column(db.Text)
    start_time = db.Column(db.DateTime(timezone=True))
    solve_time = db.Column(db.DateTime(timezone=True))
    archive_time = db.Column(db.DateTime(timezone=True))
    delete_request = db.Column(db.DateTime(timezone=True))
    delete_time = db.Column(db.DateTime(timezone=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._round = None
        self._notes = None

    @classmethod
    async def get_or_create(cls, guild_id: int, channel_id: int, **kwargs):
        """query puzzle data, create if it does not exist"""
        puzzle = await cls.query.where(
            (cls.guild_id == guild_id) &
            (cls.channel_id == channel_id)
        ).gino.first()
        if puzzle is None:
            puzzle = await cls.create(
                guild_id=guild_id,
                channel_id = channel_id,
                **kwargs
            )
        return puzzle
    
    @classmethod
    async def puzzles_in_round(cls, round_id: int):
        puzzles = await cls.query.where(
            (cls.round_id == round_id) &
            (cls.delete_time == None)
        ).gino.all()
        return puzzles

    def is_solved(self):
        return self.status == "solved" and self.solve_time is not None

    async def query_notes(self):
        notes = await PuzzleNotes.query.where(
            PuzzleNotes.puzzle_id == self.id
        ).gino.all()
        return list(notes)

    async def commit_note(self, note_text: str, **kwargs):
        added_time = datetime.datetime.now(tz=pytz.UTC)
        assert self.id >= 0
        return await PuzzleNotes.create(
            puzzle_id=self.id,
            text=note_text,
            added_time=added_time,
            **kwargs
        )


class PuzzleNotes(db.Model):
    __tablename__ = "puzzle_notes"

    note_id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    puzzle_id = db.Column(db.BIGINT,
                         db.ForeignKey("puzzle_data.id",
                                       onupdate="CASCADE", ondelete="CASCADE"),
                        nullable=False)
    # note_index = db.Column(db.Integer)
    text = db.Column(db.Text)
    user = db.Column(db.Text)
    jump_url = db.Column(db.Text)
    added_time = db.Column(db.DateTime(timezone=True))