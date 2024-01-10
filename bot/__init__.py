import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from bot import utils, database
from bot.database.models import GuildSettings

__version__ = "0.1.0"

invite_link = (
    "https://discordapp.com/api/oauth2/authorize?client_id={}&scope=bot&permissions=377957125136"
)


class SkipDatabaseLogs(logging.Filter):
    def filter(self, record):
        return record.name != "gino.engine._SAEngine"


async def get_prefix(_bot, message):
    prefix = utils.config.prefix
    if not isinstance(message.channel, discord.DMChannel):
        prefix = utils.get_guild_prefix(_bot, message.guild.id)
    return commands.when_mentioned_or(prefix)(_bot, message)


intents = discord.Intents(messages=True, message_content=True, guilds=True)
bot = commands.AutoShardedBot(command_prefix=get_prefix, intents=intents)
bot.version = __version__
bot.guild_data = {}


async def preload_guild_data():
    guilds = await GuildSettings.query.gino.all()
    d = dict()
    for guild in guilds:
        d[guild.id] = {"prefix": guild.prefix}
    return d


@bot.event
async def on_ready():
    await database.setup()
    bot.invite = invite_link.format(bot.user.id)
    bot.guild_data = await preload_guild_data()
    guild_names = [g.name for g in bot.guilds]
    guild_ids = [g.id for g in bot.guilds]

    print(
        f"""Logged in as {bot.user}..
        Serving {len(bot.users)} users in {len(bot.guilds)} guilds: {guild_names} {guild_ids}
        Invite: {invite_link.format(bot.user.id)}
    """
    )

    # Start up any loops which run against the database
    for key in bot.cogs:
        try:
            bot.cogs[key].begin_loops()
        except AttributeError:
            pass

    # Sync any slash commands to the server, if not in debug mode.
    # This is to avoid getting rate-limited while doing a bunch of development restarts.
    if utils.config.debug:
        print("Debug mode, not syncing slash commands")
    else:
        synced = await bot.tree.sync()
        print(f"Synched {len(synced)} commands")


def setup_logger(log_level=logging.INFO):
    # Set up basic logging as per https://discordpy.readthedocs.io/en/latest/logging.html#logging-setup
    logger = logging.getLogger()  # 'discord')
    logger.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    handler.addFilter(SkipDatabaseLogs())
    logger.addHandler(handler)

    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(log_level)
    discord_logger.addHandler(handler)


def extensions():
    files = Path("bot", "cogs").rglob("*.py")
    for file in files:
        yield file.as_posix()[:-3].replace("/", ".")


async def load_extensions(_bot):
    for ext in extensions():
        try:
            await _bot.load_extension(ext)
        except Exception as ex:
            print(f"Failed to load extension {ext} - exception: {ex}")


async def main():
    setup_logger(logging.INFO)
    async with bot:
        await load_extensions(bot)
        await bot.start(utils.config.token)


def run():
    asyncio.run(main())
