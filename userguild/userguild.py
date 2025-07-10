from redbot.core import commands
import discord
import re
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

    async def _join_guild(self, invite_code):
    url = f"https://discord.com/api/v10/invites/{invite_code}"
    headers = {
        "Authorization": self.user_token,
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
    }

    async with self.session.post(url, headers=headers, json={}) as resp:
        if resp.status == 429:
            data = await resp.json()
            retry_after = data.get("retry_after", 1)
            await asyncio.sleep(retry_after)
            return await self._join_guild(invite_code)
        elif resp.status == 200:
            return await resp.json()
        else:
            text = await resp.text()
            raise Exception(f"Failed with status {resp.status}: {text}")

    @commands.is_owner()
    @commands.command()
    async def addguild(self, ctx, invite_link: str):
        """Join a guild using an invite (user token only)."""
        if not self.user_token:
            await ctx.send("User token not set. Use `[p]settoken` first.")
            return

        match = re.search(r"(?:discord\.gg/|discord.com/invite/)([a-zA-Z0-9-]+)", invite_link)
        if not match:
            await ctx.send("Invalid invite link.")
            return

        invite_code = match.group(1)

        try:
            data = await self._join_guild(invite_code)
            guild_name = data.get("guild", {}).get("name", "Unknown")
            await ctx.send(f"Successfully joined guild: {guild_name}")
            await asyncio.sleep(2)
        except Exception as e:
            await ctx.send(f"Failed to join guild: {e}")

    @commands.command()
    async def checkguild(self, ctx, user_id: int):
        """Check mutual guilds with the user ID."""
        mutual_guilds = []
        for guild in self.bot.guilds:
            if guild.get_member(user_id):
                mutual_guilds.append(guild.name)

        if mutual_guilds:
            guild_list = "\n".join(f"- {g}" for g in mutual_guilds)
            await ctx.send(f"Mutual guilds with user {user_id}:\n{guild_list}")
        else:
            await ctx.send(f"No mutual guilds found with user {user_id}.")
