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

    def is_solved(self):
        return self.status == "solved" and self.solve_time is not None


