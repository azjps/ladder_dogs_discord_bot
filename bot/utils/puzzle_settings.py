from dataclasses import dataclass
import os
from pathlib import Path

from dataclasses_json import dataclass_json

DATA_DIR = Path(__file__).parent.parent.parent / "data"
if "LADDER_SPOT_DATA_DIR" in os.environ:
    # TODO: move to config.json??
    DATA_DIR = Path(os.environ["LADDER_SPOT_DATA_DIR"])


@dataclass_json
@dataclass
class GuildSettings:
    guild_id: int
    guild_name: str = ""
    hunt_url: str = ""
    hunt_url_sep: str = "_"         # Separator in the puzzle url, e.g. - for https://./puzzle/foo-bar
    hunt_round_url: str = ""        # If specified, a different url to use for rounds, defaults to hunt_url
    discord_bot_channel: str = ""   # Channel to listen for bot commands
    discord_bot_emoji: str = ":ladder: :dog:"  # Short description string or emoji for bot messages
    discord_use_voice_channels: int = 1  # Whether to create voice channels for puzzles
    drive_parent_id: str = ""       # ID of root drive folder
    drive_nexus_sheet_id: str = ""  # Refer to gsheet_nexus.py
    drive_resources_id: str = ""    # Document with resources links, etc


class GuildSettingsDb:
    cached_settings = {}

    @classmethod
    def get(cls, guild_id: int) -> GuildSettings:
        settings_path = DATA_DIR / str(guild_id) / "settings.json"
        if settings_path.exists():
            with settings_path.open() as fp:
                settings = GuildSettings.from_json(fp.read())
        else:
            # Populate empty settings file
            settings = GuildSettings(guild_id=guild_id)
            cls.commit(settings)
        return settings

    @classmethod
    def get_cached(cls, guild_id: int) -> GuildSettings:
        if guild_id in cls.cached_settings:
            return cls.cached_settings[guild_id]
        settings = cls.get(guild_id)
        cls.cached_settings[guild_id] = settings
        return settings

    @classmethod
    def commit(cls, settings: GuildSettings):
        settings_path = DATA_DIR / str(settings.guild_id) / "settings.json"
        settings_path.parent.parent.mkdir(exist_ok=True)
        settings_path.parent.mkdir(exist_ok=True)
        with settings_path.open("w") as fp:
            fp.write(settings.to_json(indent=4))
        cls.cached_settings[settings.guild_id] = settings
