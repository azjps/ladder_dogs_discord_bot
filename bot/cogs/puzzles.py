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
        print(f'{type(self).__name__} Cog ready.')

    def clean_name(self, name):
        """Cleanup name to be appropriate for discord channel"""
        name = name.strip()
        if (name[0] == name[-1]) and name.startswith(("'", '"')):
            name = name[1:-1]
        return "-".join(name.lower().split())

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send('You do not have the correct role for this command.')
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

    async def get_or_create_channel(self, guild, category, channel_name, channel_type, **kwargs):
        if channel_type == "text":
            channel_type = discord.ChannelType.text
        elif channel_type == "voice":
            channel_type = discord.ChannelType.voice
        if not (channel_type is discord.ChannelType.text or channel_type is discord.ChannelType.voice):
            raise ValueError(f"Unrecognized channel_type: {channel_type}")
        channel = discord.utils.get(
            guild.channels,
            category=category,
            type=channel_type,
            name=channel_name,
        )
        created = False
        if not channel:
            print(f"Creating a new channel: {channel_name} for category: {category}")
            create_method = guild.create_text_channel if channel_type is discord.ChannelType.text else guild.create_voice_channel
            channel = await create_method(channel_name, category=category, **kwargs)
            created = True
            
        return (channel, created)

    async def create_puzzle_channel(self, ctx, round_name, puzzle_name):
        guild = ctx.guild
        category_name = self.clean_name(round_name)
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            raise ValueError(f"Round {category_name} not found")

        channel_name = self.clean_name(puzzle_name)
        text_channel, created_text = await self.get_or_create_channel(guild=guild, category=category, channel_name=channel_name, channel_type="text", reason=self.PUZZLE_REASON)
        voice_channel, created_voice = await self.get_or_create_channel(guild=guild, category=category, channel_name=channel_name, channel_type="voice", reason=self.PUZZLE_REASON)
        created = created_text or created_voice
        if created:
            await ctx.send(f":white_check_mark: I've created new puzzle text and voice channels for {category.mention}: {text_channel.mention}")
        else:
            await ctx.send(f"I've found an already existing puzzle channel for {category.mention}: {text_channel.mention}")
        return (text_channel, voice_channel, created)

    @commands.command(aliases=["r"])
    async def round(self, ctx, *, arg):
        """*Create new puzzle round: !r round-name*"""
        category_name = self.clean_name(arg)
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            print(f'Creating a new channel category for round: {category_name}')
            category = await guild.create_category(category_name)

        await self.create_puzzle_channel(ctx, category.name, self.META_CHANNEL_NAME)


def setup(bot):
    bot.add_cog(Puzzles(bot))
