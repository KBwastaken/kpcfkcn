from redbot.core import commands
import discord
import aiohttp
import asyncio

class UserTokenGuildManager(commands.Cog):
    """Manage guilds using a user token (hypothetical & against ToS)."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.user_token = None

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.is_owner()
    @commands.command()
    async def settoken(self, ctx, *, token: str):
        """Set the user token to use."""
        self.user_token = token
        await ctx.send("User token set. Be careful with this!")

    @commands.command()
    async def checkguild(self, ctx, user_id: int):
        """Check mutual guilds with the user ID, with debug output."""
        mutual_guilds = []
        total_checked = 0
        for guild in self.bot.guilds:
            total_checked += 1
            try:
                member = guild.get_member(user_id)
                if not member:
                    member = await guild.fetch_member(user_id)
                if member:
                    mutual_guilds.append(guild.name)
                    print(f"User {user_id} found in guild: {guild.name}")
                else:
                    print(f"User {user_id} NOT found in guild: {guild.name}")
            except Exception as e:
                print(f"Error checking guild {guild.name}: {e}")

        if mutual_guilds:
            guild_list = "\n".join(f"- {g}" for g in mutual_guilds)
            await ctx.send(f"Mutual guilds with user {user_id}:\n{guild_list}")
        else:
            await ctx.send(f"No mutual guilds found with user {user_id}.")

        await ctx.send(f"Checked {total_checked} guild{'s' if total_checked != 1 else ''}.")
