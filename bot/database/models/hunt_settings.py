import datetime
import json
from typing import Dict, List

import pytz

from bot.database import db


class HuntSettings(db.Model):
    __tablename__ = "hunt_settings"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    guild_id = db.Column(db.BIGINT, db.ForeignKey("guilds.id", onupdate="CASCADE"))
    hunt_name = db.Column(db.Text)
    hunt_url = db.Column(db.Text)
    hunt_url_sep = db.Column(
        db.Text, default="_"
    )  # Separator in the puzzle url, e.g. - for https://./puzzle/foo-bar
    hunt_round_url = db.Column(
        db.Text
    )  # If specified, a different url to use for rounds, defaults to hunt_url
    drive_hunt_folder_id = db.Column(db.Text)  # The directory for all of this hunt's spreadsheets
    drive_nexus_sheet_id = db.Column(db.Text)  # Refer to gsheet_nexus.py
    drive_resources_id = db.Column(
        db.Text
    )  # Document with resources links, etc; can override GuildSettings.drive_resources_id
    start_time = db.Column(db.DateTime(timezone=True))
    end_time = db.Column(db.DateTime(timezone=True))  # If set, indicates hunt no longer active

    __table_args__ = (
        db.UniqueConstraint(guild_id, hunt_name, name="uq_hunt_settings_guild_id_hunt_name"),
    )

    @classmethod
    async def get_or_create_by_name(cls, guild_id: int, hunt_name: str):
        """query hunt settings, create if it does not exist"""
        settings = await cls.query.where(
            (cls.guild_id == guild_id) & (cls.hunt_name == hunt_name)
        ).gino.first()
        if settings is None:
            start_time = datetime.datetime.now(tz=pytz.UTC)
            settings = await cls.create(
                guild_id=guild_id,
                hunt_name=hunt_name,
                start_time=start_time,
            )
        return settings

    @classmethod
    async def get_active_hunts(cls, guild_id: int) -> List["HuntSettings"]:
        settings = await cls.query.where(
            (cls.guild_id == guild_id) & (cls.end_time.is_(None))
        ).gino.all()
        return settings

    @classmethod
    def column_type(cls, column_name):
        return getattr(cls, column_name).type.python_type

    @classmethod
    async def get_id_for_name(cls, guild_id: int, name: str):
        hunt = await HuntSettings.query.where(
            (HuntSettings.hunt_name == name) & (HuntSettings.guild_id == guild_id)
        ).gino.first()
        if hunt is None:
            return None
        return hunt.id

    async def set(self, values: Dict[str, str]):
        for key in values:
            if self.column_type(key) == int:
                values[key] = int(values[key])
        await self.update(**values).apply()

    def to_json(self):
        return json.dumps(
            {
                k: getattr(self, k)
                for k in (
                    "guild_id",
                    "hunt_name",
                    "hunt_url",
                    "hunt_url_sep",
                    "hunt_round_url",
                    "drive_hunt_folder_id",
                    "drive_nexus_sheet_id",
                    "drive_resources_id",
                )
            },
            indent=4,
        )


class HuntNotFoundError(RuntimeError):
    pass
