from redbot.core import commands
import discord
import aiohttp
import asyncio
import re

class UserTokenGuildManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.user_token = None

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.is_owner()
    @commands.command()
    async def settoken(self, ctx, *, token: str):
        """Set the user token (dangerous!)."""
        self.user_token = token
        # Patch bot's http token for fetch_member etc to work with user token
        self.bot.http.token = token
        await ctx.send("User token set (use carefully).")

    @commands.is_owner()
    @commands.command()
    async def addguild(self, ctx, invite_link: str):
        """Join guild via invite using user token (raw HTTP)."""
        if not self.user_token:
            await ctx.send("Set user token first with settoken.")
            return

        match = re.search(r"(?:discord\.gg/|discord.com/invite/)([a-zA-Z0-9-]+)", invite_link)
        if not match:
            await ctx.send("Invalid invite link.")
            return

        invite_code = match.group(1)

        url = f"https://discord.com/api/v10/invites/{invite_code}"
        headers = {
            "Authorization": self.user_token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        async with self.session.post(url, headers=headers, json={}) as resp:
            if resp.status == 200:
                data = await resp.json()
                guild_name = data.get("guild", {}).get("name", "Unknown")
                await ctx.send(f"Successfully joined guild: {guild_name}")
            else:
                text = await resp.text()
                await ctx.send(f"Failed to join guild: {resp.status} - {text}")

    @commands.is_owner()
    @commands.command()
    async def checkguild(self, ctx, user_id: int):
        """Check mutual guilds with a user ID."""
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
            except Exception:
                continue

        if mutual_guilds:
            await ctx.send(f"Mutual guilds with user {user_id}:\n" + "\n".join(f"- {g}" for g in mutual_guilds))
        else:
            await ctx.send(f"No mutual guilds found with user {user_id}.")

        await ctx.send(f"Checked {total_checked} guild{'s' if total_checked != 1 else ''}.")
