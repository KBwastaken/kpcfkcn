from redbot.core import commands, Config
import discord
import re

class GuildTracker(commands.Cog):
    """Track servers and check if users are in any of them."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=987654321)
        self.config.register_global(added_guilds=[])

    @commands.command()
    @commands.is_owner()
    async def addguild(self, ctx, invite: str):
        """Add a guild using an invite link. The bot will join and track it."""
        match = re.search(r"(?:https?://)?discord(?:\.gg|app\.com/invite)/([a-zA-Z0-9-]+)", invite)
        if not match:
            await ctx.send("Invalid invite format.")
            return

        code = match.group(1)
        try:
            invite_obj = await self.bot.fetch_invite(code, with_counts=False)
            guild = await self.bot.accept_invite(invite_obj)
        except Exception as e:
            await ctx.send(f"Could not join the server: `{e}`")
            return

        guilds = await self.config.added_guilds()
        if guild.id in guilds:
            await ctx.send(f"Already tracking **{guild.name}**.")
        else:
            guilds.append(guild.id)
            await self.config.added_guilds.set(guilds)
            await ctx.send(f"Joined and now tracking **{guild.name}**.")

    @commands.command()
    @commands.is_owner()
    async def checkguilds(self, ctx, user: discord.User):
        """Check if the user is in any of the tracked servers."""
        guilds = await self.config.added_guilds()
        found_in = []

        for guild_id in guilds:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            member = guild.get_member(user.id)
            if member:
                found_in.append(guild.name)

        if found_in:
            await ctx.send(f"{user.mention} is in: **{', '.join(found_in)}**")
        else:
            await ctx.send(f"{user.mention} is not in any tracked servers.")
