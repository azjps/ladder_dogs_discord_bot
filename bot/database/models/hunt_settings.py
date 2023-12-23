import textwrap
from typing import Dict

from bot.database import db


class HuntSettings(db.Model):
    __tablename__ = "hunt_settings"

    id = db.Column(db.BIGINT, primary_key=True, autoincrement=True)
    guild_id = db.Column(db.BIGINT)
    hunt_name = db.Column(db.Text)
    hunt_url = db.Column(db.Text)
    hunt_url_sep = db.Column(db.Text, default = "_")                # Separator in the puzzle url, e.g. - for https://./puzzle/foo-bar
    hunt_round_url = db.Column(db.Text)                             # If specified, a different url to use for rounds, defaults to hunt_url
    drive_hunt_folder_id = db.Column(db.Text)                       # The directory for all of this hunt's spreadsheets
    drive_nexus_sheet_id = db.Column(db.Text)                       # Refer to gsheet_nexus.py

    @classmethod
    async def get_or_create_by_name(cls, guild_id: int, hunt_name: str):
        """query hunt settings, create if it does not exist"""
        settings = await cls.query.where(
            (cls.guild_id == guild_id) &
            (cls.hunt_name == hunt_name)
        ).gino.first()
        if settings is None:
            settings = await cls.create()
            await settings.update(
                guild_id=guild_id,
                hunt_name = hunt_name
            ).apply()
        return settings

    # I don't love managing this way, but I can't find anything in SQLAlchemy about introspecting columns after they're created.
    def column_type(self, column_name):
        if column_name in ["guild_id"]:
            return int
        return str

    @classmethod
    async def get_id_for_name(cls, guild_id: int, name: str):
        hunt = await HuntSettings.query.where(
            (HuntSettings.hunt_name == name) &
            (HuntSettings.guild_id == guild_id)
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
        return textwrap.dedent(f"""
               {{ "guild_id": {self.guild_id},
                 "hunt_name": {self.hunt_name},
                 "hunt_url": "{self.hunt_url}",
                 "hunt_url_sep": "{self.hunt_url_sep}",
                 "hunt_round_url": "{self.hunt_round_url}",
                 "drive_hunt_folder_id": "{self.drive_hunt_folder_id}",
                 "drive_nexus_sheet_id": "{self.drive_nexus_sheet_id}",
               }}
        """).strip()

class HuntNotFoundError(RuntimeError):
    pass
