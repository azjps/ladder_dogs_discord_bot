import textwrap
from typing import Dict

from bot.database import db


class GuildSettings(db.Model):
    __tablename__ = "guilds"

    id = db.Column(db.BIGINT, primary_key=True)
    prefix = db.Column(db.Text)
    guild_name = db.Column(db.Text)
    discussion_channel = db.Column(
        db.Text, default="general"
    )  # The name of the channel for meta-hunt discussions
    discord_bot_channel = db.Column(db.Text)  # Channel to listen for bot commands
    discord_bot_emoji = db.Column(db.Text)  # Short description string or emoji for bot messages
    discord_use_voice_channels = db.Column(
        db.BIGINT, default=1
    )  # Whether to create voice channels for puzzles
    drive_parent_id = db.Column(db.Text)  # ID of root drive folder
    drive_resources_id = db.Column(db.Text)  # Document with resources links, etc
    drive_starter_sheet_id = db.Column(
        db.Text
    )  # Document that is copied to create all puzzle sheets
    archive_delay = db.Column(db.Integer, default=300)  # Delay for items to be archived, in seconds

    @classmethod
    async def get_or_create(cls, guild_id: int) -> "GuildSettings":
        """query guild, create if it does not exist"""
        guild = await cls.get(guild_id)
        if guild is None:
            guild = await cls.create(id=guild_id)
        return guild

    @classmethod
    def column_type(cls, column_name):
        return getattr(cls, column_name).type.python_type

    async def set(self, values: Dict[str, str]):
        for key in values:
            if self.column_type(key) == int:
                values[key] = int(values[key])
        await self.update(**values).apply()

    def to_json(self):
        # TODO: use json.dumps() & mapper.attrs
        # https://stackoverflow.com/questions/2537471/method-of-iterating-over-sqlalchemy-models-defined-columns
        return textwrap.dedent(
            f"""
               {{ "guild_id": {self.id},
                 "prefix": "{self.guild_name}",
                 "guild_name": "{self.guild_name}",
                 "discussion_channel": "{self.discussion_channel}",
                 "discord_bot_channel": "{self.discord_bot_channel}",
                 "discord_bot_emoji": "{self.discord_bot_emoji}",
                 "discord_use_voice_channels": {self.discord_use_voice_channels},
                 "drive_parent_id": "{self.drive_parent_id}",
                 "drive_resources_id": "{self.drive_resources_id}"
                 "drive_starter_sheet_id": "{self.drive_starter_sheet_id}"
                 "archive_delay": "{self.archive_delay}"
               }}
        """
        ).strip()
