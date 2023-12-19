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
import bot.database.models  # noqa


async def setup():
    await db.set_bind(utils.config.database)


async def shutdown():
    await db.pop_bind().close()


async def query_guild(guild_id: int):
    """query guild, create if not exist"""
    guild = await models.GuildSettings.get(guild_id)
    if guild is None:
        guild = await models.GuildSettings.create(id=guild_id)
    return guild

async def query_hunt_settings(guild_id: int):
    """query hunt settings, create if not exist"""
    settings = await models.HuntSettings.get(guild_id)
    if settings is None:
        settings = await models.HuntSettings.create(guild_id=guild_id)
    return settings

async def query_puzzle_data(guild_id: int, channel_id: int):
    """query puzzle data, create if not exist"""
    puzzle = await models.PuzzleData.query.where(
        (models.PuzzleData.guild_id == guild_id) &
        (models.PuzzleData.channel_id == channel_id)
    ).gino.first()
    if puzzle is None:
        puzzle = await models.PuzzleData.create()
        await puzzle.update(
            guild_id=guild_id,
            channel_id = channel_id
        ).apply()
    return puzzle
