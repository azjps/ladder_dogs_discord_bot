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
    guild_id: int = 0
    guild_name: str = ""
    hunt_url: str = ""
    discord_bot_channel: str = ""  # channel to listen for bot commands
    drive_parent_id: str = ""
    drive_nexus_sheet_id: str = ""


class GuildSettingsDb:
    def get(guild_id: int) -> GuildSettings:
        settings_path = DATA_DIR / str(guild_id) / "settings.json"
        if settings_path.exists():
            with settings_path.open() as fp:
                settings = GuildSettings.from_json(fp.read())
        else:
            settings = GuildSettings(guild_id=guild_id)
            with settings_path.open("w") as fp:
                fp.write(settings.to_json(indent=4))
        return settings
