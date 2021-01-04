from pathlib import Path

import discord
from discord.ext import commands


class Puzzles(commands.Cog):
    META_CHANNEL_NAME = "meta"
    META_REASON = "bot-meta"
    PUZZLE_REASON = "bot-puzzle"

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
            category = await guild.create_category(category_name)

        await self.create_puzzle_channel(ctx, category.name, self.META_CHANNEL_NAME)

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
            print(f"Creating a new channel: {channel_name} for category: {category}")
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
            await self.send_initial_puzzle_channel_messages(text_channel)

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
            value="""This channel and the corresponding voice channel 
are goods places to discuss how to tackle this puzzle. Usually you'll
want to do most of the puzzle work on Google Sheets / Docs.
""",
            inline=False,
        )
        embed.add_field(
            name="Commands",
            value="""The following may be useful discord commands:

• `!solve SOLUTION` will mark this puzzle as solved and archive this channel to #solved-puzzles
• `!link` will show the puzzle's link on the hunt website, and `!link <url>` will update the link
• `!doc` will show Google Sheet link, and `!doc <url>` will update the link
* `!res` or `!resources` will show links to some useful puzzling resources
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

    def check_if_puzzle_channel(self, ctx):
        return True

    @commands.command()
    async def info(self, ctx):
        if not self.check_if_puzzle_channel(ctx):
            await self.send_not_puzzle_channel(ctx.channel)
            return

        await self.send_initial_puzzle_channel_messages(ctx.channel)

    @commands.command()
    async def link(self, ctx):
        if not self.check_if_puzzle_channel(ctx):
            await self.send_not_puzzle_channel(ctx)
            return

        embed = discord.Embed(
            description=f"""Puzzle Hunt link: """
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["sheet"])
    async def doc(self, ctx):
        if not self.check_if_puzzle_channel(ctx):
            await self.send_not_puzzle_channel(ctx)
            return

        embed = discord.Embed(
            description=f"""Google Drive link: """
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["res"])
    async def resources(self, ctx):
        if not self.check_if_puzzle_channel(ctx):
            await self.send_not_puzzle_channel(ctx)
            return

        embed = discord.Embed(
            description=f"""Resources: """
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def solve(self, ctx, *, arg):
        if not self.check_if_puzzle_channel(ctx):
            await self.send_not_puzzle_channel(ctx)
            return

        solution = arg.strip().upper()
        embed = discord.Embed(
            description=f"""Solved! Marked the solution as `{solution}`"""
        )
        await ctx.send(embed=embed)

class _PuzzleJsonDb:
    def __init__(self, dir_path: Path):
        self.dir_path = dir_path

def setup(bot):
    bot.add_cog(Puzzles(bot))
