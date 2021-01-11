import datetime
import logging
from typing import Optional

import discord
from discord.ext import commands
import pytz

from bot.utils import urls
from bot.utils.puzzles_data import MissingPuzzleError, PuzzleData, PuzzleJsonDb

logger = logging.getLogger(__name__)


class Puzzles(commands.Cog):
    META_CHANNEL_NAME = "meta"
    META_REASON = "bot-meta"
    PUZZLE_REASON = "bot-puzzle"
    DELETE_REASON = "bot-delete"

    def __init__(self, bot):
        self.bot = bot

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

    @commands.command(aliases=["p"])
    async def puzzle(self, ctx, *, arg):
        """*Create new puzzle channels: !p round-name: puzzle-name*"""
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

        if ":" in arg:
            round_name, puzzle_name = arg.split(":", 1)
            return await self.create_puzzle_channel(ctx, round_name, puzzle_name)

        raise ValueError(f"Unable to parse puzzle name {arg}, try using `!p round-name: puzzle-name`")

    @commands.command(aliases=["r"])
    async def round(self, ctx, *, arg):
        """*Create new puzzle round: !r round-name*"""
        category_name = self.clean_name(arg)
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            print(f"Creating a new channel category for round: {category_name}")
            # TODO: debug position?
            category = await guild.create_category(category_name, position=len(guild.categories) - 2)

        await self.create_puzzle_channel(ctx, category.name, self.META_CHANNEL_NAME)

    @commands.command(aliases=["list"])
    async def list_puzzles(self, ctx):
        """*List all puzzles and their statuses*"""
        all_puzzles = PuzzleJsonDb.get_all(ctx.guild.id)
        # TODO: this is very primitive
        message = ""
        for puzzle in all_puzzles:
            message += f"{puzzle.round_name} {puzzle.channel_mention} {puzzle.puzzle_type} {puzzle.status}\n"

        embed = discord.Embed()
        embed.add_field(
            name="Puzzles",
            value=message,
        )
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
        guild = ctx.guild
        category_name = self.clean_name(round_name)
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            raise ValueError(f"Round {category_name} not found")

        channel_name = self.clean_name(puzzle_name)
        text_channel, created_text = await self.get_or_create_channel(
            guild=guild, category=category, channel_name=channel_name, channel_type="text", reason=self.PUZZLE_REASON
        )
        if created_text:
            puzzle_data = PuzzleData(
                name=channel_name,
                round_name=category_name,
                guild_name=guild.name,
                guild_id=guild.id,
                channel_mention=text_channel.mention,
                channel_id=text_channel.id,
                start_time=datetime.datetime.now(tz=pytz.UTC),
            )
            PuzzleJsonDb.commit(puzzle_data)
            await self.send_initial_puzzle_channel_messages(text_channel)

            gsheet_cog = self.bot.get_cog("GoogleSheets")
            print("google sheets cog:", gsheet_cog)
            if gsheet_cog is not None:
                # update google sheet ID
                await gsheet_cog.create_puzzle_spreadsheet(text_channel, puzzle_data)

        voice_channel, created_voice = await self.get_or_create_channel(
            guild=guild, category=category, channel_name=channel_name, channel_type="voice", reason=self.PUZZLE_REASON
        )
        created = created_text or created_voice
        if created:
            await ctx.send(
                f":white_check_mark: I've created new puzzle text and voice channels for {category.mention}: {text_channel.mention}"
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
• `!status extracting` will update the status of the puzzle, for others to know
""",
            inline=False,
        )
        await channel.send(embed=embed)

    async def send_not_puzzle_channel(self, ctx):
        await ctx.send("This does not appear to be a puzzle channel")

    def get_puzzle_data_from_channel(self, channel) -> Optional[PuzzleData]:
        if not channel.category:
            return None

        guild_id = channel.guild.id
        round_name = channel.category.name
        puzzle_name = channel.name
        try:
            return PuzzleJsonDb.get(guild_id, puzzle_name, round_name)
        except MissingPuzzleError:
            return None

    @commands.command()
    async def info(self, ctx):
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
        await channel.send(embed=embed)

    @commands.command()
    async def link(self, ctx, *, url: Optional[str]):
        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "hunt_url", url, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if url else None
            )

    @commands.command(aliases=["sheet"])
    async def doc(self, ctx, *, url: Optional[str]):
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

    @commands.command()
    async def status(self, ctx, *, status: Optional[str]):
        puzzle_data = await self.update_puzzle_attr_by_command(ctx, "status", status, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if status else None
            )

    @commands.command()
    async def type(self, ctx, *, puzzle_type: Optional[str]):
        await self.update_puzzle_attr_by_command(ctx, "puzzle_type", puzzle_type, reply=False)
        if puzzle_data:
            await self.send_state(
                ctx.channel, puzzle_data, description=":white_check_mark: I've updated:" if puzzle_type else None
            )

    @commands.command(aliases=["res"])
    async def resources(self, ctx):
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        embed = discord.Embed(description=f"""Resources: """)
        await ctx.send(embed=embed)

    @commands.command()
    async def solve(self, ctx, *, arg):
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        solution = arg.strip().upper()
        puzzle_data.status = "solved"
        puzzle_data.solution = solution
        puzzle_data.solve_time = datetime.datetime.now(tz=pytz.UTC)
        PuzzleJsonDb.commit(puzzle_data)

        embed = discord.Embed(
            description=f":ladder: :dog: :partying_face: Great work! Marked the solution as `{solution}`"
        )
        embed.add_field(
            name="Follow-up",
            value="If the solution was mistakenly entered, please message `!unsolve`. "
            "Otherwise, I will automatically archive this puzzle channel to #solved-puzzles "
            "and archive the Spreadsheet in around 5 minutes.",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def unsolve(self, ctx):
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        prev_solution = puzzle_data.solution
        puzzle_data.status = "unsolved"
        puzzle_data.solution = ""
        puzzle_data.solve_time = None
        PuzzleJsonDb.commit(puzzle_data)

        embed = discord.Embed(
            description=f":ladder: :dog: Alright, I've unmarked {prev_solution} as the solution. "
            "You'll get'em next time!"
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def delete(self, ctx):
        """Permanently delete a channel"""
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        if puzzle_data.solution:
            raise ValueError("Unable to delete a solved puzzle channel, please contact discord admins if needed")

        channel = ctx.channel
        category = channel.category

        # TODO: need to confirm deletion first!

        PuzzleJsonDb.delete(puzzle_data)
        voice_channel = discord.utils.get(
            ctx.guild.channels, category=category, type=discord.ChannelType.voice, name=channel.name
        )
        if voice_channel:
            await voice_channel.delete(reason=self.DELETE_REASON)
        # delete text channel last so that errors can be reported
        await ctx.channel.delete(reason=self.DELETE_REASON)

    @commands.command()
    async def debug_puzzle_channel(self, ctx):
        puzzle_data = self.get_puzzle_data_from_channel(ctx.channel)
        if not puzzle_data:
            await self.send_not_puzzle_channel(ctx)
            return

        await ctx.channel.send(f"```json\n{puzzle_data.to_json()}```")

    async def archive_solved_puzzles(self, guild: discord.Guild) -> list[PuzzleData]:
        """TODO: have this as an event task:
        https://discordpy.readthedocs.io/en/latest/ext/tasks/
        """
        puzzles_to_archive = PuzzleJsonDb.get_solved_puzzles_to_archive(guild.id)
        # need to stash guild as a botvar:
        # https://stackoverflow.com/questions/64676968/how-to-use-context-within-discord-ext-tasks-loop-in-discord-py
        # channel = .get(channel)
        # TODO: read this from config?
        solved_category_name = "SOLVED PUZZLES"
        solved_category = discord.utils.get(guild.categories, name=solved_category_name)
        if not solved_category:
            avail_categories = [c.name for c in guild.categories]
            raise ValueError(
                f"{solved_category_name} category does not exist; available categories: {avail_categories}"
            )
        
        gsheet_cog = self.bot.get_cog("GoogleSheets")

        for puzzle in puzzles_to_archive:
            channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.text, id=puzzle.channel_id
            )
            if channel:
                await channel.edit(category=solved_category)

            voice_channel = discord.utils.get(
                guild.channels, type=discord.ChannelType.voice, name=puzzle.name
            )
            if voice_channel:
                await voice_channel.delete()

            if gsheet_cog:
                await gsheet_cog.archive_puzzle_spreadsheet(puzzle)

            puzzle.archive_time = datetime.datetime.now(tz=pytz.UTC)
            puzzle.archive_channel_mention = channel.mention
            PuzzleJsonDb.commit(puzzle)
        return puzzles_to_archive

    @commands.command()
    async def archive_solved(self, ctx):
        """Archive solved puzzles
        
        Done automatically on task loop, so this is only useful for debugging
        """
        puzzles_to_archive = await self.archive_solved_puzzles(ctx.guild)
        mentions = " ".join([p.channel_mention for p in puzzles_to_archive])
        message = f"Archived {len(puzzles_to_archive)} solved puzzle channels: {mentions}"
        logger.info(message)
        await ctx.send(message)

def setup(bot):
    bot.add_cog(Puzzles(bot))
