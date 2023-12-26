from bot.database import db


class PuzzleData(db.Model):
    __tablename__ = "puzzle_data"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.Text)
    round_name = db.Column(db.Text)
    round_id = db.Column(db.BIGINT, default=0) # round = category channel
    solved_round_id = db.Column(db.BIGINT, default=0)
    guild_id = db.Column(db.BIGINT, default=0)
    guild_name = db.Column(db.Text)
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

    @classmethod
    async def get_or_create(cls, guild_id: int, channel_id: int):
        """query puzzle data, create if it does not exist"""
        puzzle = await cls.query.where(
            (cls.guild_id == guild_id) &
            (cls.channel_id == channel_id)
        ).gino.first()
        if puzzle is None:
            puzzle = await cls.create()
            await puzzle.update(
                guild_id=guild_id,
                channel_id = channel_id
            ).apply()
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

