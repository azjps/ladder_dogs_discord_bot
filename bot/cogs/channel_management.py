import datetime
import logging
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
import pytz

from bot.base_cog import BaseCog, GeneralAppError
from bot.data.puzzle_db import PuzzleDb
from bot import database
from bot.database.models import PuzzleData, RoundData

logger = logging.getLogger(__name__)


class ChannelManagement(BaseCog):
    PUZZLE_REASON = "bot-puzzle"
    DELETE_REASON = "bot-delete"
    SOLVED_PUZZLES_CATEGORY_PREFIX = "SOLVED-"

    def __init__(self, bot):
        self.bot = bot

    def begin_loops(self):
        logger.info("Beginning loops")
        self.archived_solved_puzzles_loop.start()

    def clean_name(self, name):
        """Cleanup name to be appropriate for discord channel"""
        name = name.strip()
        if (name[0] == name[-1]) and name.startswith(("'", '"')):
            name = name[1:-1]
        return "-".join(name.lower().split())

    @app_commands.command()
    async def puzzle(
        self,
        interaction: discord.Interaction,
        *,
        hunt_round: Optional[str],
        puzzle: str,
        url: Optional[str],
    ):
        """*Create new puzzle channels: /puzzle round-name: puzzle-name*

        Can be posted in either a #general channel or the bot channel
        """
        # settings = await database.query_guild(interaction.guild.id)
        if not hunt_round:
            category = interaction.channel.category
            if category and category.name != "Text Channels":
                if hunt_round is None:
                    hunt_round = category.name
                if hunt_round != category.name:
                    raise ValueError(f"Unexpected round: {hunt_round}, expected: {category.name}")
                return await self.create_puzzle_channel(interaction, hunt_round, puzzle, url)

        if not (await self.check_is_bot_channel(interaction)):
            return

        if hunt_round is None:
            raise ValueError(
                f"Unable to parse hunt for puzzle name {puzzle}, try using `/puzzle round-name puzzle-name`"
            )

        return await self.create_puzzle_channel(interaction, hunt_round, puzzle, url)

    @app_commands.command()
    async def round(
        self, interaction: discord.Interaction, *, category_name: str, hunt_name: Optional[str]
    ):
        """*Create new puzzle round: /round round-name*"""
        await self.create_round(interaction, category_name, hunt_name)

    @app_commands.command()
    async def hunt(self, interaction: discord.Interaction, *, hunt_url: str, hunt_name: str):
        """*Create a new hunt*"""
        if not (await self.check_is_bot_channel(interaction)):
            return

        settings = await database.query_hunt_settings_by_name(interaction.guild.id, hunt_name)
        await settings.update(hunt_url=hunt_url).apply()

        (text_channel, _, _) = await self.create_round(interaction, hunt_name, hunt_name)

        gsheet_cog = self.bot.get_cog("GoogleSheets")
        if gsheet_cog is not None:
            # Create the drive folder and nexus sheet for this hunt
            await gsheet_cog.create_hunt_drive(interaction.guild.id, text_channel, settings)

    @app_commands.command()
    async def create_hunt_drive(self, interaction: discord.Interaction):
        hunt = await database.query_hunt_settings_by_round(
            interaction.guild.id, interaction.channel.category.id
        )
        if hunt.hunt_name is None:
            raise GeneralAppError(
                f"Channel {interaction.channel.category.name}/{interaction.channel.name} does not appear to be a part of a hunt"
            )
        gsheet_cog = self.bot.get_cog("GoogleSheets")
        await interaction.response.send_message("Creating folder and sheet for this hunt")
        if gsheet_cog is not None:
            # Create the drive folder and nexus sheet for this hunt
            await gsheet_cog.create_hunt_drive(interaction.guild.id, interaction.channel, hunt)

    async def create_round(
        self, interaction: discord.Interaction, category_name: str, hunt_name: Optional[str]
    ):
        """Handle creating a round for either the round or hunt command"""
        if not (await self.check_is_bot_channel(interaction)):
            return

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            logger.info(f"Creating a new channel category for round: {category_name}")
            # Normally place this category as the two from the end, unless it's the only channel or the second channel, then place it at the end.
            new_position = len(guild.categories) - 2
            if new_position < 1:
                new_position = len(guild.categories)
            category = await guild.create_category(category_name, position=new_position)
            from_category = 0
            if interaction.channel.category:
                from_category = interaction.channel.category.id
            await RoundData.create_round(
                guild_id=guild.id,
                from_category=from_category,
                category=category.id,
                name=category_name,
                hunt=hunt_name,
            )

        settings = await database.query_guild(interaction.guild.id)
        return await self.create_puzzle_channel(
            interaction, category.name, settings.discussion_channel, None
        )

    async def get_or_create_channel(
        self, guild, category: discord.CategoryChannel, channel_name: str, channel_type, **kwargs
    ):
        """Retrieve given channel by name/category or create one"""
        if channel_type == "text":
            channel_type = discord.ChannelType.text
        elif channel_type == "voice":
            channel_type = discord.ChannelType.voice
        if not (
            channel_type is discord.ChannelType.text or channel_type is discord.ChannelType.voice
        ):
            raise ValueError(f"Unrecognized channel_type: {channel_type}")
        channel = discord.utils.get(
            guild.channels, category=category, type=channel_type, name=channel_name
        )
        created = False
        if not channel:
            message = f"Creating a new channel: {channel_name} of type {channel_type} for category: {category}"
            print(message)
            logger.info(message)
            create_method = (
                guild.create_text_channel
                if channel_type is discord.ChannelType.text
                else guild.create_voice_channel
            )
            channel = await create_method(channel_name, category=category, **kwargs)
            created = True

        return (channel, created)

    async def create_puzzle_channel(
        self, interaction, round_name: str, puzzle_name: str, url: Optional[str]
    ):
        """Create new text channel for puzzle, and optionally a voice channel

        Save puzzle metadata to data_dir, send initial messages to channel, and
        create corresponding Google Sheet if GoogleSheets cog is set up.
        """
        await interaction.response.send_message(
            f"Creating channel(s) for puzzle {puzzle_name}", ephemeral=True
        )
        guild = interaction.guild
        category_name = round_name
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            raise ValueError(f"Round {category_name} not found")

        channel_name = self.clean_name(puzzle_name)
        text_channel, created_text = await self.get_or_create_channel(
            guild=guild,
            category=category,
            channel_name=channel_name,
            channel_type="text",
            reason=self.PUZZLE_REASON,
        )
        guild_settings = await database.query_guild(guild.id)
        hunt_settings = await database.query_hunt_settings_by_round(guild.id, category.id)
        round_settings = await database.query_round_data(guild.id, category.id)
        if created_text:
            if not url and hunt_settings.hunt_url:
                # NOTE: this is a heuristic and may need to be updated!
                # This is based on last year's URLs, where the URL format was
                # https://<site>/puzzle/puzzle_name
                url_sep = round_settings.round_url_sep or hunt_settings.hunt_url_sep
                # NOTE: in some years, there may be a different website for
                # a round, so can adjust urls on a per-round basis
                url_base = round_settings.round_url
                if url_base:
                    url_base = url_base.rstrip("/")
                else:
                    url_base = hunt_settings.hunt_url.rstrip("/")
                if channel_name == guild_settings.discussion_channel:
                    url_name = category_name.lower().replace("-", url_sep)
                    # Use the round name in the URL
                    hunt_round_base = url_base
                    if hunt_settings.hunt_round_url:
                        hunt_round_base = hunt_settings.hunt_round_url.rstrip("/")
                    url = f"{hunt_round_base}/{url_name}"
                else:
                    url_name = channel_name.lower().replace("-", url_sep)
                    url = f"{url_base}/{url_name}"
            puzzle_data = await database.query_puzzle_data(
                guild_id=interaction.guild.id,
                channel_id=text_channel.id,
                round_id=category.id,
            )
            await puzzle_data.update(
                name=channel_name,
                round_name=category_name,
                round_id=category.id,
                guild_name=guild.name,
                channel_mention=text_channel.mention,
                hunt_url=url,
                start_time=datetime.datetime.now(tz=pytz.UTC),
            ).apply()
            await text_channel.send(
                embed=self.build_channel_info_message(
                    guild_settings.discussion_channel, text_channel
                )
            )

            if channel_name == guild_settings.discussion_channel and channel_name != "meta":
                await puzzle_data.update(puzzle_type="discussion").apply()
            else:
                gsheet_cog = self.bot.get_cog("GoogleSheets")
                if gsheet_cog is not None:
                    # update google sheet ID
                    await gsheet_cog.create_puzzle_spreadsheet(text_channel, puzzle_data)
        else:
            puzzle_data = await self.get_puzzle_data_from_channel(text_channel)

        created_voice = False
        if guild_settings.discord_use_voice_channels:
            voice_channel, created_voice = await self.get_or_create_channel(
                guild=guild,
                category=category,
                channel_name=channel_name,
                channel_type="voice",
                reason=self.PUZZLE_REASON,
            )
            if created_voice:
                await puzzle_data.update(voice_channel_id=voice_channel.id).apply()

        created = created_text or created_voice
        if created:
            if created_text and created_voice:
                created_desc = "text and voice"  # I'm sure there's a more elegant way to do this ..
            elif created_text:
                created_desc = "text"
            elif created_voice:
                created_desc = "voice"

            await interaction.followup.send(
                f":white_check_mark: I've created new puzzle {created_desc} channels for {category.mention}: {text_channel.mention}"
            )
        else:
            await interaction.followup.send(
                f"I've found an already existing puzzle channel for {category.mention}: {text_channel.mention}"
            )
        return (text_channel, voice_channel, created)

    def build_channel_info_message(self, discussion_channel: str, channel: discord.TextChannel):
        """Builds intro message for a puzzle or discussion channel"""
        if channel.name == discussion_channel:
            embed = discord.Embed(
                description=f"""Welcome to the general discussion channel for {channel.category.mention}!"""
            )
            embed.add_field(
                name="Overview",
                value="This channel and the corresponding voice channel are goods places to discuss "
                "the round itself. Usually you'll want to discuss individual puzzles in their "
                "respective channels.",
                inline=False,
            )
            embed.add_field(
                name="Commands",
                value="""The following may be useful discord commands:
• `/puzzle PUZZLE NAME` will create a new puzzle in this round.
• `/info` will re-post this message
• `/status puzzle-name` will update the status of the round, for others to know
• `/note flavortext clues braille` can be used to leave a note about ideas/progress in the round
""",
                inline=False,
            )
            return embed
        else:  # This is a puzzle channel
            embed = discord.Embed(
                description=f"""Welcome to the puzzle channel for {channel.mention} in {channel.category.mention}!"""
            )
            embed.add_field(
                name="Overview",
                value="This channel and the corresponding voice channel "
                "are goods places to discuss how to tackle this puzzle. Usually you'll "
                "want to do most of the puzzle work itself on Google Sheets / Docs.",
                inline=False,
            )
            embed.add_field(
                name="Commands",
                value="""The following may be useful discord commands:
• `/solve SOLUTION` will mark this puzzle as solved and archive this channel to #solved-puzzles
• `/link <url>` will update the link to the puzzle on the hunt website
• `/doc <url>` will update the Google Drive link
• `/info` will re-post this message
• `/delete` should *only* be used if a channel was mistakenly created.
• `/type crossword` will mark the type of the puzzle, for others to know
• `/priority high` will mark the priority of the puzzle, for others to know
• `/status extracting` will update the status of the puzzle, for others to know
• `/note flavortext clues braille` can be used to leave a note about ideas/progress
""",
                inline=False,
            )
            return embed

    async def send_not_puzzle_channel(self, interaction):
        await interaction.response.send_message("This does not appear to be a puzzle channel")

    @app_commands.command()
    async def delete(self, interaction: discord.Interaction):
        """*Permanently delete a channel, after a timeout*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        if puzzle_data.solution:
            raise ValueError(
                "Unable to delete a solved puzzle channel, please contact discord admins if needed"
            )

        await PuzzleDb.request_delete(puzzle_data)
        logger.info(f"Scheduling deletion for puzzle: {puzzle_data.name}")

        settings = await database.query_guild(interaction.guild.id)
        emoji = settings.discord_bot_emoji
        embed = discord.Embed(
            description=f"{emoji} :recycle: Okay {interaction.user.mention}, I will permanently delete this channel in ~5 minutes."
        )
        embed.add_field(
            name="Follow-up",
            value="If you didn't mean to delete this channel, please message `/undelete`. "
            "Otherwise, in around 5 minutes, I will automatically delete this "
            "puzzle channel.",
        )
        await interaction.response.send_message(embed=embed)

    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def cleanup_deleted_channels(self, interaction: discord.Interaction):
        """*(admin) Mark manually deleted channels as deleted in the backend*"""
        all_puzzles = await PuzzleDb.get_all(interaction.guild.id)
        count = 0
        for puzzle in all_puzzles:
            if puzzle.delete_time is None:
                if self.bot.get_channel(puzzle.channel_id) is None:
                    count = count + 1
                    logger.info(f"Marking channel {puzzle.round_name}/{puzzle.name} as deleted")
                    await PuzzleDb.delete(puzzle)
        embed = discord.Embed(
            description=f"Swept through channels, marked {count} missing channels as deleted in the backend."
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def undelete(self, interaction: discord.Interaction):
        """*Prevent channel from getting deleted before timeout*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        if puzzle_data.status == "deleting" or puzzle_data.delete_time is not None:
            await puzzle_data.update(status="", delete_time=None).apply()
            logger.info(f"Un-scheduling deletion for puzzle: {puzzle_data.name}")

            settings = await database.query_guild(interaction.guild.id)
            emoji = settings.discord_bot_emoji
            await interaction.response.send_message(
                f"{emoji} Noted, will no longer be deleting this channel."
            )
        else:
            await interaction.response.send_message(
                ":exclamation: Channel isn't being deleted, nothing to undelete"
            )

    async def process_deleted_puzzles(self, guild: discord.Guild):
        """Deletes puzzles for which sufficient time has elapsed since being marked for deletion.

        Delete the channels and mark it as deleted in the database.
        """
        puzzles_to_delete = await PuzzleDb.get_puzzles_to_delete(guild.id)

        delete_reason = "User requested deletion"
        for puzzle in puzzles_to_delete:
            assert (
                puzzle.delete_request is not None
                and puzzle.solve_time is None
                and puzzle.archive_time is None
            )
            logger.info(f"Deleting puzzle: {puzzle.name}")

            text_channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.text, id=puzzle.channel_id
            )
            await self.delete_voice_channel(guild, puzzle, reason=delete_reason)
            await PuzzleDb.delete(puzzle)
            # delete text channel last so that errors can be reported
            await text_channel.delete(reason=self.DELETE_REASON)

    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def delete_now(self, interaction: discord.Interaction):
        """*(admin) Permanently delete a channel*"""
        puzzle_data = await self.get_puzzle_data_from_channel(interaction.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(interaction)
            return

        if puzzle_data.solution:
            raise ValueError(
                "Unable to delete a solved puzzle channel, please contact discord admins if needed"
            )

        channel = interaction.channel
        category = channel.category

        # TODO: need to confirm deletion first!
        voice_channel = discord.utils.get(
            interaction.guild.channels,
            category=category,
            type=discord.ChannelType.voice,
            name=channel.name,
        )
        if voice_channel:
            await voice_channel.delete(reason=self.DELETE_REASON)
        await PuzzleDb.delete(puzzle_data)
        # delete text channel last so that errors can be reported
        await interaction.channel.delete(reason=self.DELETE_REASON)

    @commands.has_permissions(manage_channels=True)
    @app_commands.command()
    async def delete_all(
        self, interaction: discord.Interaction, base_url: str, dry_run: bool = True
    ):
        """*(admin) Permanently delete a channel*

        The current syntax is `/delete_all {base_url:str} {dry_run:bool}`
        and will delete all puzzle channels whose puzzle URL starts with `base_url`.
        """
        # Ideally in the future we would use a stricter identifier for hunt
        # instead of base_url. For now just a simple check that not inputting
        # an empty string.
        if not base_url or len(base_url) <= len("https://"):
            logger.error("base_url required for delete_all")
            await interaction.response.send_message(
                ":exclamation: base_url required for delete_all"
            )
            return

        puzzles = await PuzzleDb.get_all(interaction.guild.id)
        # TODO: use a hunt identifier instead
        puzzles_found = [
            p for p in puzzles if p.hunt_url is not None and p.hunt_url.startswith(base_url)
        ]
        if not puzzles_found:
            await interaction.response.send_message(
                f":exclamation: No puzzles found for {base_url}"
            )
            return

        # TODO: how to confirm deletions?
        await self.confirm_delete_all(interaction, puzzles_found, dry_run=dry_run)

    async def confirm_delete_all(
        self, interaction, puzzles: List[PuzzleData], dry_run: bool = False
    ):
        """Actually delete puzzles and channels"""
        for puzzle in puzzles:
            try:
                reason = "delete all puzzles from hunt"

                # delete text channel last so that errors can be reported
                text_channel = discord.utils.get(
                    interaction.guild.channels, type=discord.ChannelType.text, id=puzzle.channel_id
                )
                if dry_run:
                    logger.info(
                        f"Deleting puzzle {puzzle.round_name}:{puzzle.name} {puzzle.channel_id}, found text_channel: {text_channel}"
                    )
                else:
                    await self.delete_voice_channel(interaction.guild, puzzle, reason=reason)

                    if text_channel:
                        try:
                            await text_channel.delete(reason=reason)
                        except discord.errors.NotFound:
                            logger.exception(
                                f"Unable to delete text_channel {text_channel} for puzzle {puzzle.name}"
                            )
                    # Make sure the database entry is flagged as deleted.
                    await PuzzleDb.delete(puzzle)
            except Exception:
                logger.exception(f"Unable to delete puzzle: {puzzle.name}")

        await interaction.response.send_message(f"Deleted {len(puzzles)} puzzle channels")

    async def delete_voice_channel(
        self, guild: discord.Guild, puzzle: PuzzleData, reason: Optional[str] = None
    ):
        """If found, delete associated voice channel"""
        voice_channel: Optional[discord.VoiceChannel] = None
        if puzzle.voice_channel_id:
            voice_channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.voice, id=puzzle.voice_channel_id
            )
        if not voice_channel:
            voice_channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.voice, name=puzzle.name
            )

        if voice_channel:
            try:
                await voice_channel.delete(reason=reason)
            except discord.errors.NotFound:
                logger.exception(
                    f"Unable to find voice channel to delete: {voice_channel} for puzzle {puzzle.name}"
                )

    async def get_or_create_solved_category(
        self, guild: discord.Guild, puzzle: PuzzleData
    ) -> discord.CategoryChannel:
        solved_category = None
        if puzzle.solved_round_id:
            solved_category = discord.utils.get(guild.categories, id=puzzle.solved_round_id)

        if not solved_category:
            solved_category_name = self.SOLVED_PUZZLES_CATEGORY_PREFIX + puzzle.round_name
            solved_category = discord.utils.get(guild.categories, name=solved_category_name)

        if not solved_category:
            position = len(guild.categories) - 1
            open_category = discord.utils.get(guild.categories, id=puzzle.round_id)
            if open_category:
                position = open_category.position

            logger.info(
                f"Creating a new channel category for solved puzzles in round: {solved_category_name}"
                f" at position {position}"
            )
            solved_category = await guild.create_category(solved_category_name, position=position)

        round_data = await database.query_round_data(guild.id, puzzle.round_id)
        await round_data.update(solved_category_id=solved_category.id).apply()
        return solved_category

    async def archive_solved_puzzles(self, guild: discord.Guild) -> List[PuzzleData]:
        """Archive puzzles for which sufficient time has elapsed since solve time

        Move them to a solved-puzzles channel category, and rename spreadsheet
        to start with the text [SOLVED]
        """
        puzzles_to_archive = await PuzzleDb.get_solved_puzzles_to_archive(guild.id)
        if len(puzzles_to_archive) == 0:
            return puzzles_to_archive
        logger.info(f"Found {len(puzzles_to_archive)} to archive: {puzzles_to_archive}")
        gsheet_cog = self.bot.get_cog("GoogleSheets")

        for puzzle in puzzles_to_archive:
            solved_category = await self.get_or_create_solved_category(guild, puzzle)

            channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.text, id=puzzle.channel_id
            )
            if channel:
                await channel.edit(category=solved_category)

            await self.delete_voice_channel(guild, puzzle, reason="archiving solved puzzle")

            if gsheet_cog:
                await gsheet_cog.archive_puzzle_spreadsheet(puzzle)

            channel_mention = None
            if channel:
                channel_mention = channel.mention
            await puzzle.update(
                archive_time=datetime.datetime.now(tz=pytz.UTC),
                archive_channel_mention=channel_mention,
                solved_round_id=solved_category.id,
            ).apply()
        return puzzles_to_archive

    @app_commands.command()
    async def archive_solved(self, interaction: discord.Interaction):
        """*(admin) Archive solved puzzles. Done automatically*

        Done automatically on task loop, so this is only useful for debugging
        """
        if not (await self.check_is_bot_channel(interaction)):
            return
        puzzles_to_archive = await self.archive_solved_puzzles(interaction.guild)
        mentions = " ".join([p.channel_mention for p in puzzles_to_archive])
        message = f"Archived {len(puzzles_to_archive)} solved puzzle channels: {mentions}"
        logger.info(message)
        await interaction.response.send_message(message)

    @tasks.loop(seconds=30.0)
    async def archived_solved_puzzles_loop(self):
        """Ref: https://discordpy.readthedocs.io/en/latest/ext/tasks/"""
        for guild in self.bot.guilds:
            try:
                await self.archive_solved_puzzles(guild)
            except Exception:
                logger.exception(
                    f"Unable to archive solved puzzles for guild {guild.id} {guild.name}"
                )
            try:
                await self.process_deleted_puzzles(guild)
            except Exception:
                logger.exception(f"Unable to delete puzzles for guild {guild.id} {guild.name}")

    @archived_solved_puzzles_loop.before_loop
    async def before_archiving(self):
        await self.bot.wait_until_ready()
        logger.info("Ready to start archiving solved puzzles")


async def setup(bot):
    await bot.add_cog(ChannelManagement(bot))
