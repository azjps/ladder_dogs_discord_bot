from bot import utils
from gino import Gino

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = Gino(naming_convention=naming_convention)

# import models so Gino can register them
import bot.database.models as models  # noqa


async def setup():
    await db.set_bind(utils.config.database)


async def shutdown():
    await db.pop_bind().close()


async def query_guild(guild_id: int):
    """query guild, create if it does not exist"""
    return await models.GuildSettings.get_or_create(guild_id)

async def query_hunt_settings_by_name(guild_id: int, hunt_name: str):
    """query hunt settings, create if it does not exist"""
    return await models.HuntSettings.get_or_create_by_name(guild_id, hunt_name)

async def query_hunt_settings_by_round(guild_id: int, round_channel: int):
    return await models.RoundData.get_hunt_from_round(guild_id, round_channel)

async def query_puzzle_data(guild_id: int, channel_id: int, **kwargs):
    """query puzzle data, create if it does not exist"""
    return await models.PuzzleData.get_or_create(guild_id, channel_id, **kwargs)

async def query_round_data(guild_id: int, category_id: int):
    """query round data, create if it does not exist"""
    return await models.RoundData.get_or_create(category_id)

