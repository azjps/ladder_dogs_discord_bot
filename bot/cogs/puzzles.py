import datetime
import json
import logging
from typing import List, Optional

import discord
from discord.channel import VoiceChannel
from discord.ext import commands, tasks
import pytz

from bot.utils import urls
from bot.utils.puzzles_data import MissingPuzzleError, PuzzleData, PuzzleJsonDb
from bot import database
from bot.database.models import HuntSettings

logger = logging.getLogger(__name__)


class Puzzles(commands.Cog):
    META_CHANNEL_NAME = "meta"
    META_REASON = "bot-meta"
    PUZZLE_REASON = "bot-puzzle"
    DELETE_REASON = "bot-delete"
    SOLVED_PUZZLES_CATEGORY_PREFIX = "SOLVED-"
    PRIORITIES = ["low", "medium", "high", "very high"]

    def __init__(self, bot):
        self.bot = bot
        self.archived_solved_puzzles_loop.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{type(self).__name__} Cog ready.")

    def clean_name(self, name):
        """Cleanup name to be appropriate for discord channel"""
        name = name.strip()
        if (name[0] == name[-1]) and name.startswith(("'", '"')):
            name = name[1:-1]
        return "-".join(name.lower().split())

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # if isinstance(error, commands.errors.CheckFailure):
        #     await ctx.send('You do not have the correct role for this command.')
        await ctx.send(":exclamation: " + str(error))

    async def check_is_bot_channel(self, ctx) -> bool:
        """Check if command was sent to bot channel configured in settings"""
        settings = await database.query_hunt_settings(ctx.guild.id)
        if not settings.discord_bot_channel:
            # If no channel is designated, then all channels are fine
            # to listen to commands.
            return True

        if ctx.channel.name == settings.discord_bot_channel:
            # Channel name matches setting (note, channel name might not be unique)
            return True

        await ctx.send(f":exclamation: Most bot commands should be sent to #{settings.discord_bot_channel}")
        return False

    @commands.command(aliases=["p"])
    async def puzzle(self, ctx, *, arg):
        """*Create new puzzle channels: !p round-name: puzzle-name*

        Can be posted in either a #meta channel or the bot channel
        """
        guild = ctx.guild
        if ctx.channel.name == "meta":
            category = ctx.channel.category
            if ":" in arg:
                round_name, puzzle_name = arg.split(":", 1)
                if self.clean_name(round_name) != category:
                    # Check current category matches given round name
                    raise ValueError(f"Unexpected round: {round_name}, expected: {category.name}")
            else:
                puzzle_name = arg
            return await self.create_puzzle_channel(ctx, category.name, puzzle_name)

        if not (await self.check_is_bot_channel(ctx)):
            return

        if ":" in arg:
            round_name, puzzle_name = arg.split(":", 1)
            return await self.create_puzzle_channel(ctx, round_name, puzzle_name)

        raise ValueError(f"Unable to parse puzzle name {arg}, try using `!p round-name: puzzle-name`")

    @commands.command(aliases=["r"])
    async def round(self, ctx, *, arg):
        """*Create new puzzle round: !r round-name*"""
        if not (await self.check_is_bot_channel(ctx)):
            return

        category_name = self.clean_name(arg)
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            logger.info(f"Creating a new channel category for round: {category_name}")
            # TODO: debug position?
            category = await guild.create_category(category_name, position=len(guild.categories) - 2)

        await self.create_puzzle_channel(ctx, category.name, self.META_CHANNEL_NAME)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def show_settings(self, ctx):
        """*(admin) Show guild-level settings*"""
        guild_id = ctx.guild.id
        settings = await database.query_hunt_settings(guild_id)
        await ctx.channel.send(f"```json\n{settings.to_json()}```")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def update_setting(self, ctx, setting_key: str, setting_value: str):
        """*(admin) Update guild setting: !update_setting key value*"""
        guild_id = ctx.guild.id
        settings = await database.query_hunt_settings(guild_id)
        if hasattr(settings, setting_key):
            old_value = getattr(settings, setting_key)
            #setattr(settings, setting_key, setting_value)
            await settings.update(**{setting_key: setting_value}).apply()
            await ctx.send(f":white_check_mark: Updated `{setting_key}={setting_value}` from old value: `{old_value}`")
        else:
            await ctx.send(f":exclamation: Unrecognized setting key: `{setting_key}`. Use `!show_settings` for more info.")

    @commands.command(aliases=["list"])
    async def list_puzzles(self, ctx):
        """*List all puzzles and their statuses*"""
        if not (await self.check_is_bot_channel(ctx)):
            return

        all_puzzles = PuzzleJsonDb.get_all(ctx.guild.id)
        all_puzzles = PuzzleData.sort_by_round_start(all_puzzles)

        embed = discord.Embed()
        cur_round = None
        message = ""
        # Create a message with a new embed field per round,
        # listing all puzzles in the embed field
        for puzzle in all_puzzles:
            if cur_round is None:
                cur_round = puzzle.round_name
            if puzzle.round_name != cur_round or len(message) >= 512:
                # Reached next round, add new embed field
                embed.add_field(name=cur_round, value=message)
                cur_round = puzzle.round_name
                message = ""
            message += f"{puzzle.channel_mention}"
            if puzzle.puzzle_type:
                message += f" type:{puzzle.puzzle_type}"
            if puzzle.solution:
                message += f" sol:**{puzzle.solution}**"
            elif puzzle.status:
                message += f" status:{puzzle.status}"
            message += "\n"

        if embed.fields:
            await ctx.send(embed=embed)

    async def get_or_create_channel(
        self, guild, category: discord.CategoryChannel, channel_name: str, channel_type, **kwargs
    ):
        """Retrieve given channel by name/category or create one"""
        if channel_type == "text":
            channel_type = discord.ChannelType.text
        elif channel_type == "voice":
            channel_type = discord.ChannelType.voice
        if not (channel_type is discord.ChannelType.text or channel_type is discord.ChannelType.voice):
            raise ValueError(f"Unrecognized channel_type: {channel_type}")
        channel = discord.utils.get(guild.channels, category=category, type=channel_type, name=channel_name)
        created = False
        if not channel:
            message = f"Creating a new channel: {channel_name} of type {channel_type} for category: {category}"
            print(message)
            logger.info(message)
            create_method = (
                guild.create_text_channel if channel_type is discord.ChannelType.text else guild.create_voice_channel
            )
            channel = await create_method(channel_name, category=category, **kwargs)
            created = True

        return (channel, created)

    async def create_puzzle_channel(self, ctx, round_name: str, puzzle_name: str):
        """Create new text channel for puzzle, and optionally a voice channel

        Save puzzle metadata to data_dir, send initial messages to channel, and
        create corresponding Google Sheet if GoogleSheets cog is set up.
        """
        guild = ctx.guild
        category_name = self.clean_name(round_name)
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            raise ValueError(f"Round {category_name} not found")

        channel_name = self.clean_name(puzzle_name)
        text_channel, created_text = await self.get_or_create_channel(
            guild=guild, category=category, channel_name=channel_name, channel_type="text", reason=self.PUZZLE_REASON
        )
        settings = await database.query_hunt_settings(guild.id)
        if created_text:
            puzzle_data = PuzzleData(
                name=channel_name,
                round_name=category_name,
                round_id=category.id,
                guild_name=guild.name,
                guild_id=guild.id,
                channel_mention=text_channel.mention,
                channel_id=text_channel.id,
                start_time=datetime.datetime.now(tz=pytz.UTC),
            )
            if settings.hunt_url:
                # NOTE: this is a heuristic and may need to be updated!
                # This is based on last year's URLs, where the URL format was
                # https://<site>/puzzle/puzzle_name
                hunt_url_base = settings.hunt_url.rstrip("/")
                if channel_name == self.META_CHANNEL_NAME:
                    # Use the round name in the URL
                    hunt_name = category_name.lower().replace("-", settings.hunt_url_sep)
                    hunt_round_base = hunt_url_base
                    if settings.hunt_round_url:
                        hunt_round_base = settings.hunt_round_url.rstrip("/")
                    puzzle_data.hunt_url = f"{hunt_round_base}/{hunt_name}"
                else:
                    hunt_name = channel_name.replace("-", settings.hunt_url_sep)
                    puzzle_data.hunt_url = f"{hunt_url_base}/{hunt_name}"
            PuzzleJsonDb.commit(puzzle_data)
            await self.send_initial_puzzle_channel_messages(text_channel)

            gsheet_cog = self.bot.get_cog("GoogleSheets")
            # print("google sheets cog:", gsheet_cog)
            if gsheet_cog is not None:
                # update google sheet ID
                await gsheet_cog.create_puzzle_spreadsheet(text_channel, puzzle_data)
        else:
            puzzle_data = self.get_puzzle_data_from_channel(text_channel)

        created_voice = False
        if settings.discord_use_voice_channels:
            voice_channel, created_voice = await self.get_or_create_channel(
                guild=guild, category=category, channel_name=channel_name, channel_type="voice", reason=self.PUZZLE_REASON
            )
            if created_voice:
                puzzle_data.voice_channel_id = voice_channel.id
                PuzzleJsonDb.commit(puzzle_data)

        created = created_text or created_voice
        if created:
            if created_text and created_voice:
                created_desc = "text and voice"  # I'm sure there's a more elegant way to do this ..
            elif created_text:
                created_desc = "text"
            elif created_voice:
                created_desc = "voice"

            await ctx.send(
                f":white_check_mark: I've created new puzzle {created_desc} channels for {category.mention}: {text_channel.mention}"
            )
        else:
            await ctx.send(
                f"I've found an already existing puzzle channel for {category.mention}: {text_channel.mention}"
            )
        return (text_channel, voice_channel, created)

    async def send_initial_puzzle_channel_messages(self, channel: discord.TextChannel):
        """Send intro message on a puzzle channel"""
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
• `!solve SOLUTION` will mark this puzzle as solved and archive this channel to #solved-puzzles
• `!link <url>` will update the link to the puzzle on the hunt website
• `!doc <url>` will update the Google Drive link
* `!info` will re-post this message
• `!delete` should *only* be used if a channel was mistakenly created.
• `!type crossword` will mark the type of the puzzle, for others to know
• `!priority high` will mark the priority of the puzzle, for others to know
• `!status extracting` will update the status of the puzzle, for others to know
• `!note flavortext clues braille` can be used to leave a note about ideas/progress
""",
            inline=False,
        )
        await channel.send(embed=embed)

    async def send_not_puzzle_channel(self, ctx):
        await ctx.send("This does not appear to be a puzzle channel")

    def get_puzzle_data_from_channel(self, channel) -> Optional[PuzzleData]:
        """Extract puzzle data based on the channel name and category name

        Looks up the corresponding JSON data
        """
        if not channel.category:
            return None

        guild = channel.guild
        guild_id = guild.id
        round_id = channel.category.id
        round_name = channel.category.name
        puzzle_id = channel.id
        puzzle_name = channel.name
        try:
            return PuzzleJsonDb.get(guild_id, puzzle_id, round_id)
        except MissingPuzzleError:
            # Not the cleanest, just try to guess the original category id
            # A DB would be useful here, then can directly query on solved_channel_id ..
            if round_name.startswith(self.SOLVED_PUZZLES_CATEGORY_PREFIX):
                og_round_name = round_name[len(self.SOLVED_PUZZLES_CATEGORY_PREFIX):]
                og_round = discord.utils.get(guild.categories, name=og_round_name)
                if og_round:
                    try:
                        return PuzzleJsonDb.get(guild_id, puzzle_id, og_round.id)
                    except MissingPuzzleError:
                        pass

            logger.error(f"Unable to retrieve puzzle={puzzle_id} round={round_id} {round_name}/{puzzle_name}")
            return None

    @commands.command()
    async def info(self, ctx):
        """*Show discord command help for a puzzle channel*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        await self.send_initial_puzzle_channel_messages(ctx.channel)

    async def update_puzzle_attr_by_command(self, ctx, attr, value, message=None, reply=True):
        """Common pattern where we want to update a single field in PuzzleData based on command"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        if puzzle_data.is_solved():
            await ctx.send(
                 ":warning: Please note that this puzzle has already been marked as solved, "
                 f"with solution `{puzzle_data.solution}`"
            )

        message = message or attr
        if value:
            setattr(puzzle_data, attr, value)
            PuzzleJsonDb.commit(puzzle_data)
            message = "Updated! " + message

        if reply:
            embed = discord.Embed(description=f"""{message}: {getattr(puzzle_data, attr)}""")
            await ctx.send(embed=embed)
        return puzzle_data

    async def send_state(self, channel: discord.TextChannel, puzzle_data: PuzzleData, description=None):
        """Send simple embed showing relevant links"""
        embed = discord.Embed(description=description)
        embed.add_field(name="Hunt URL", value=puzzle_data.hunt_url or "?")
        spreadsheet_url = urls.spreadsheet_url(puzzle_data.google_sheet_id) if puzzle_data.google_sheet_id else "?"
        embed.add_field(name="Google Drive", value=spreadsheet_url)
        embed.add_field(name="Status", value=puzzle_data.status or "?")
        embed.add_field(name="Type", value=puzzle_data.puzzle_type or "?")
        embed.add_field(name="Priority", value=puzzle_data.priority or "?")
        await channel.send(embed=embed)

    @commands.command()
    async def link(self, ctx, *, url: Optional[str]):
        """*Show or update link to puzzle*"""
        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "hunt_url", url, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if url else None
            )

    @commands.command(aliases=["sheet", "drive"])
    async def doc(self, ctx, *, url: Optional[str]):
        """*Show or update link to google spreadsheet/doc for puzzle*"""
        file_id = None
        if url:
            file_id = urls.extract_id_from_url(url)
            if not file_id:
                ctx.send(f":exclamation: Invalid Google Drive URL, unable to extract file ID: {url}")

        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "google_sheet_id", file_id, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if url else None
            )

    @commands.command(aliases=["notes"])
    async def note(self, ctx, *, note: Optional[str]):
        """*Show or add a note about the puzzle*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        message = "Showing notes left by users!"
        if note:
            puzzle_data.notes.append(f"{note} - {ctx.message.jump_url}")
            PuzzleJsonDb.commit(puzzle_data)
            message = (
                f"Added a new note! Use `!erase_note {len(puzzle_data.notes)}` to remove the note if needed. "
                f"Check `!notes` for the current list of notes."
            )

        if puzzle_data.notes:
            embed = discord.Embed(description=f"{message}")
            embed.add_field(
                name="Notes",
                value="\n".join([f"{i+1}: {puzzle_data.notes[i]}" for i in range(len(puzzle_data.notes))])
            )
        else:
            embed = discord.Embed(description="No notes left yet, use `!note my note here` to leave a note")
        await ctx.send(embed=embed)

    @commands.command()
    async def erase_note(self, ctx, note_index: int):
        """*Remove a note by index*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        if 1 <= note_index <= len(puzzle_data.notes):
            note = puzzle_data.notes[note_index-1]
            del puzzle_data.notes[note_index - 1]
            PuzzleJsonDb.commit(puzzle_data)
            description = f"Erased note {note_index}: `{note}`"
        else:
            description = f"Unable to find note {note_index}"

        embed = discord.Embed(description=description)
        embed.add_field(
            name="Notes",
            value="\n".join([f"{i+1}, {puzzle_data.notes[i]}" for i in range(len(puzzle_data.notes))])
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def status(self, ctx, *, status: Optional[str]):
        """*Show or update puzzle status, e.g. "extracting"*"""
        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "status", status, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if status else None
            )

    @commands.command()
    async def type(self, ctx, *, puzzle_type: Optional[str]):
        """*Show or update puzzle type, e.g. "crossword"*"""
        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "puzzle_type", puzzle_type, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if puzzle_type else None
            )

    @commands.command()
    async def priority(self, ctx, *, priority: Optional[str]):
        """*Show or update puzzle priority, one of "low", "medium", "high"*"""
        if priority is not None and priority not in self.PRIORITIES:
            await ctx.send(f":exclamation: Priority should be one of {self.PRIORITIES}, got \"{priority}\"")
            return

        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "priority", priority, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if priority else None
            )

    # Currently not very useful, resources also posted in Quick Links worksheet
    # @commands.command(aliases=["res"])
    # async def resources(self, ctx):
    #     puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
    #     if not puzzle_data:
    #         await self.send_not_puzzle_channel(ctx)
    #         return
    #
    #     embed = discord.Embed(description=f"""Resources: """)
    #     await ctx.send(embed=embed)

    @commands.command()
    async def solve(self, ctx, *, arg):
        """*Mark puzzle as fully solved, after confirmation from HQ*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        solution = arg.strip().upper()
        puzzle_data.status = "solved"
        puzzle_data.solution = solution
        puzzle_data.solve_time = datetime.datetime.now(tz=pytz.UTC)
        PuzzleJsonDb.commit(puzzle_data)

        emoji = await self.get_guild_settings_from_ctx(ctx).discord_bot_emoji
        embed = discord.Embed(
            description=f"{emoji} :partying_face: Great work! Marked the solution as `{solution}`"
        )
        embed.add_field(
            name="Follow-up",
            value="If the solution was mistakenly entered, please message `!unsolve`. "
            "Otherwise, in around 5 minutes, I will automatically archive this "
            "puzzle channel to #solved-puzzles and archive the Google Spreadsheet",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def unsolve(self, ctx):
        """*Mark an accidentally solved puzzle as not solved*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        prev_solution = puzzle_data.solution
        puzzle_data.status = "unsolved"
        puzzle_data.solution = ""
        puzzle_data.solve_time = None
        PuzzleJsonDb.commit(puzzle_data)

        emoji = await self.get_guild_settings_from_ctx(ctx).discord_bot_emoji
        embed = discord.Embed(
            description=f"{emoji} Alright, I've unmarked {prev_solution} as the solution. "
            "You'll get'em next time!"
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def delete(self, ctx):
        """*Permanently delete a channel, after a timeout*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        if puzzle_data.solution:
            raise ValueError("Unable to delete a solved puzzle channel, please contact discord admins if needed")

        puzzle_data.status = "deleting"
        puzzle_data.delete_time = datetime.datetime.now(tz=pytz.UTC)
        PuzzleJsonDb.commit(puzzle_data)

        logger.info(f"Scheduling deletion for puzzle: {puzzle_data.to_json()}")

        emoji = await self.get_guild_settings_from_ctx(ctx).discord_bot_emoji
        embed = discord.Embed(
            description=f"{emoji} :recycle: Okay {ctx.author.mention}, I will permanently delete this channel in ~5 minutes."
        )
        embed.add_field(
            name="Follow-up",
            value="If you didn't mean to delete this channel, please message `!undelete`. "
            "Otherwise, in around 5 minutes, I will automatically delete this "
            "puzzle channel.",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def undelete(self, ctx):
        """*Prevent channel from getting deleted before timeout*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        if puzzle_data.status == "deleting" or puzzle_data.delete_time is not None:
            puzzle_data.status = ""
            puzzle_data.delete_time = None
            PuzzleJsonDb.commit(puzzle_data)
            logger.info(f"Un-scheduling deletion for puzzle: {puzzle_data.to_json()}")

            emoji = await self.get_guild_settings_from_ctx(ctx).discord_bot_emoji
            await ctx.send(f"{emoji} Noted, will no longer be deleting this channel.")
        else:
            await ctx.send(f":exclamation: Channel isn't being deleted, nothing to undelete")

    async def cleanup_deleted_puzzles(self, guild: discord.Guild):
        """Archive puzzles for which sufficient time has elapsed since solve time

        Move them to a solved-puzzles channel category, and rename spreadsheet
        to start with the text [SOLVED]
        """
        puzzles_to_delete = PuzzleJsonDb.get_puzzles_to_delete(guild.id)

        delete_reason = "User requested deletion"
        for puzzle in puzzles_to_delete:
            assert (
                puzzle.delete_time is not None
                and puzzle.solve_time is None
                and puzzle.archive_time is None
            )
            logger.info(f"Deleting puzzle: {puzzle.to_json()}")

            await self.delete_voice_channel(guild, puzzle, reason=delete_reason)

            text_channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.text, id=puzzle.channel_id
            )
            PuzzleJsonDb.delete(puzzle)
            # delete text channel last so that errors can be reported
            await text_channel.delete(reason=self.DELETE_REASON)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def delete_now(self, ctx):
        """*(admin) Permanently delete a channel*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        if puzzle_data.solution:
            raise ValueError("Unable to delete a solved puzzle channel, please contact discord admins if needed")

        channel = ctx.channel
        category = channel.category

        # TODO: need to confirm deletion first!
        voice_channel = discord.utils.get(
            ctx.guild.channels, category=category, type=discord.ChannelType.voice, name=channel.name
        )
        if voice_channel:
            await voice_channel.delete(reason=self.DELETE_REASON)
        PuzzleJsonDb.delete(puzzle_data)
        # delete text channel last so that errors can be reported
        await ctx.channel.delete(reason=self.DELETE_REASON)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def delete_all(self, ctx, base_url: str, dry_run: bool = True):
        """*(admin) Permanently delete a channel*

        The current syntax is `!delete_all {base_url:str} {dry_run:bool}`
        and will delete all puzzle channels whose puzzle URL starts with `base_url`.
        """
        # Ideally in the future we would use a stricter identifier for hunt
        # instead of base_url. For now just a simple check that not inputting
        # an empty string.
        if not base_url or len(base_url) <= len("https://"):
            logger.error("base_url required for delete_all")
            await ctx.send(f":exclamation: base_url required for delete_all")
            return

        puzzles = PuzzleJsonDb.get_all(ctx.guild.id)
        # TODO: use a hunt identifier instead
        puzzles_found = [p for p in puzzles if p.hunt_url.startswith(base_url)]
        if not puzzles_found:
            await ctx.send(f":exclamation: No puzzles found for {base_url}")
            return

        # TODO: how to confirm deletions?
        await self.confirm_delete_all(ctx, puzzles_found, dry_run=dry_run)

    async def confirm_delete_all(self, ctx, puzzles: List[PuzzleData], dry_run: bool = False):
        """Actually delete puzzles and channels"""
        for puzzle in puzzles:
            try:
                reason = "delete all puzzles from hunt"

                # delete text channel last so that errors can be reported
                text_channel = discord.utils.get(
                    ctx.guild.channels, type=discord.ChannelType.text, id=puzzle.channel_id
                )
                if dry_run:
                    logger.info(f"Deleting puzzle {puzzle.round_name}:{puzzle.name} {puzzle.channel_id}, found text_channel: {text_channel}")
                else:
                    await self.delete_voice_channel(ctx.guild, puzzle, reason=reason)

                    if text_channel:
                        try:
                            await text_channel.delete(reason=reason)
                        except discord.errors.NotFound:
                            logger.exception(f"Unable to delete text_channel {text_channel} for puzzle {puzzle.to_json()}")
                    # TODO: delete json entries too?
                    # PuzzleJsonDb.delete(puzzle)
            except Exception:
                logger.exception(f"Unable to delete puzzle: {puzzle.to_json()}")

        await ctx.send(f"Deleted {len(puzzles)} puzzle channels")

    # async def confirm_delete(self, ctx):
    #     ref: https://github.com/stroupbslayen/discord-pretty-help/blob/master/pretty_help/pretty_help.py
    #     embed = discord.Embed(description="Are you sure you wish to delete this channel? All of this channel's contents will be permanently deleted.")
    #     message: discord.Message = await ctx.send(embed=embed)
    #     message.add_reaction()
    #     payload: discord.RawReactionActionEvent = await bot.wait_for(
    #         "raw_reaction_add", timeout=self.active_time, check=check
    #     )

    @commands.command()
    async def debug_puzzle_channel(self, ctx):
        """*(admin) See puzzle metadata*"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        await ctx.channel.send(f"```json\n{puzzle_data.to_json()}```")

    async def delete_voice_channel(self, guild: discord.Guild, puzzle: PuzzleData, reason: Optional[str] = None):
        """If found, delete associated voice channel"""
        voice_channel : Optional[discord.VoiceChannel] = None
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
                logger.exception(f"Unable to find voice channel to delete: {voice_channel} for puzzle {puzzle.to_json()}")

    async def get_or_create_solved_category(self, guild: discord.Guild, puzzle: PuzzleData) -> discord.CategoryChannel:
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

        return solved_category

    async def archive_solved_puzzles(self, guild: discord.Guild, minutes: Optional[int] = None) -> List[PuzzleData]:
        """Archive puzzles for which sufficient time has elapsed since solve time

        Move them to a solved-puzzles channel category, and rename spreadsheet
        to start with the text [SOLVED]
        """
        puzzles_to_archive = PuzzleJsonDb.get_solved_puzzles_to_archive(guild.id, minutes=minutes)
        # logger.info(f"Found {len(puzzles_to_archive)} to archive: {puzzles_to_archive}")
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

            puzzle.archive_time = datetime.datetime.now(tz=pytz.UTC)
            puzzle.archive_channel_mention = channel.mention if channel else None
            puzzle.solved_round_id = solved_category.id
            PuzzleJsonDb.commit(puzzle)
        return puzzles_to_archive

    @commands.command()
    async def archive_solved(self, ctx, *, minutes: Optional[int]):
        """*(admin) Archive solved puzzles. Done automatically*

        Done automatically on task loop, so this is only useful for debugging
        """
        if not (await self.check_is_bot_channel(ctx)):
            return
        puzzles_to_archive = await self.archive_solved_puzzles(ctx.guild, minutes=minutes)
        mentions = " ".join([p.channel_mention for p in puzzles_to_archive])
        message = f"Archived {len(puzzles_to_archive)} solved puzzle channels: {mentions}"
        logger.info(message)
        await ctx.send(message)

    @tasks.loop(seconds=30.0)
    async def archived_solved_puzzles_loop(self):
        """Ref: https://discordpy.readthedocs.io/en/latest/ext/tasks/"""
        for guild in self.bot.guilds:
            try:
                await self.archive_solved_puzzles(guild)
            except Exception:
                logger.exception(f"Unable to archive solved puzzles for guild {guild.id} {guild.name}")
            try:
                await self.cleanup_deleted_puzzles(guild)
            except Exception:
                logger.exception(f"Unable to delete puzzles for guild {guild.id} {guild.name}")

    @archived_solved_puzzles_loop.before_loop
    async def before_archiving(self):
        await self.bot.wait_until_ready()
        logger.info("Ready to start archiving solved puzzles")

async def setup(bot):
    await bot.add_cog(Puzzles(bot))
