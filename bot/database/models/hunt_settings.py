import textwrap
from typing import Dict

from bot.database import db


class HuntSettings(db.Model):
    __tablename__ = "hunt_settings"

    guild_id = db.Column(db.BIGINT, primary_key=True)
    guild_name = db.Column(db.Text)
    hunt_url = db.Column(db.Text)
    hunt_url_sep = db.Column(db.Text, default = "_")                # Separator in the puzzle url, e.g. - for https://./puzzle/foo-bar
    hunt_round_url = db.Column(db.Text)                             # If specified, a different url to use for rounds, defaults to hunt_url
    discussion_channel = db.Column(db.Text, default = "general")    # The name of the channel for meta-hunt discussions
    discord_bot_channel = db.Column(db.Text)                        # Channel to listen for bot commands
    discord_bot_emoji = db.Column(db.Text)                          # Short description string or emoji for bot messages
    discord_use_voice_channels = db.Column(db.BIGINT, default = 1)  # Whether to create voice channels for puzzles
    drive_parent_id = db.Column(db.Text)                            # ID of root drive folder
    drive_nexus_sheet_id = db.Column(db.Text)                       # Refer to gsheet_nexus.py
    drive_resources_id = db.Column(db.Text)                         # Document with resources links, etc
    archive_delay = db.Column(db.Integer, default = 300)            # Delay for items to be archived, in seconds

    # I don't love managing this way, but I can't find anything in SQLAlchemy about introspecting columns after they're created.
    def column_type(self, column_name):
        if column_name in [
            "guild_id",
            "discord_use_voice_channels",
            "archive_delay"]:
            return int
        return str

    async def set(self, values: Dict[str, str]):
        for key in values:
            if self.column_type(key) == int:
                values[key] = int(values[key])
        await self.update(**values).apply()

    def to_json(self):
        return textwrap.dedent(f"""
               {{ "guild_id": {self.guild_id},
                 "guild_name": "{self.guild_name}",
                 "hunt_url": "{self.hunt_url}",
                 "hunt_url_sep": "{self.hunt_url_sep}",
                 "hunt_round_url": "{self.hunt_round_url}",
                 "discussion_channel": "{self.discussion_channel}",
                 "discord_bot_channel": "{self.discord_bot_channel}",
                 "discord_bot_emoji": "{self.discord_bot_emoji}",
                 "discord_use_voice_channels": {self.discord_use_voice_channels},
                 "drive_parent_id": "{self.drive_parent_id}",
                 "drive_nexus_sheet_id": "{self.drive_nexus_sheet_id}",
                 "drive_resources_id": "{self.drive_resources_id}"
                 "archive_delay": "{self.archive_delay}"
               }}
        """).strip()

