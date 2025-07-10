from redbot.core import commands
import aiohttp
import asyncio

class UserTokenGuildChecker(commands.Cog):
    """Check mutual guilds using a user token (handle with care)."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

        # Hardcoded user token here (handle safely!)
        self.user_token = "MTM5Mjk1NzkxNjI5Nzk1MzM1MA.G2iAL2.rr3-z2k9m4l7837HTJJRW_xWKqwLwWtGoXEQgU"

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.command()
    async def checkguild(self, ctx, user_id: int):
        """Check which guilds your user token account and <user_id> share."""
        if not self.user_token:
            await ctx.send("User token not set.")
            return

        headers = {
            "Authorization": self.user_token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/112.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }

        async with self.session.get("https://discord.com/api/v10/users/@me/guilds", headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                await ctx.send(f"Failed to fetch user guilds: {resp.status} - {text}")
                return
            guilds = await resp.json()

        mutual_guilds = []
        total_checked = 0

        for guild in guilds:
            total_checked += 1
            guild_id = guild["id"]
            url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"

            async with self.session.get(url, headers=headers) as member_resp:
                if member_resp.status == 200:
                    mutual_guilds.append(guild["name"])
            await asyncio.sleep(0.25)  # avoid ratelimits

        if mutual_guilds:
            await ctx.send(f"Mutual guilds with user {user_id}:\n" + "\n".join(f"- {g}" for g in mutual_guilds))
        else:
            await ctx.send(f"No mutual guilds found with user {user_id}.")

        await ctx.send(f"Checked {total_checked} guild{'s' if total_checked != 1 else ''}.")
