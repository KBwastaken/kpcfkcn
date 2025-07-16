import discord
from redbot.core import commands, Config, checks
from discord.ext import tasks
from typing import Optional

OAUTH2_SCOPES = ["identify", "email", "guilds", "guilds.join"]


class AuthCog(commands.Cog):
    """OAuth authorization and admin commands."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(
            admins=[],
            forced_users={},
            allowadmin={},
            emails={},
            client_id=None,
            client_secret=None,
            redirect_uri="https://example.com/callback"  # Change this if needed
        )
        self.loop_check_forced_users.start()

    def cog_unload(self):
        self.loop_check_forced_users.cancel()

    async def check_admin(self, ctx):
        admins = await self.config.admins()
        return ctx.author.id in admins

    @checks.is_owner()
    @commands.command()
    async def authsetclientid(self, ctx, *, client_id: str):
        """Set the OAuth2 client ID."""
        await self.config.client_id.set(client_id)
        await ctx.send("OAuth2 Client ID saved.")

    @checks.is_owner()
    @commands.command()
    async def authsetsecret(self, ctx, *, client_secret: str):
        """Set the OAuth2 client secret."""
        await self.config.client_secret.set(client_secret)
        await ctx.send("OAuth2 Client Secret saved.")

    async def get_oauth_url(self, state: Optional[str] = None) -> Optional[str]:
        client_id = await self.config.client_id()
        client_secret = await self.config.client_secret()
        redirect_uri = await self.config.redirect_uri()
        if not client_id or not client_secret:
            return None
        scopes = "%20".join(OAUTH2_SCOPES)
        base = "https://discord.com/api/oauth2/authorize"
        url = (
            f"{base}?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scopes}"
        )
        if state:
            url += f"&state={state}"
        return url

@commands.command()
async def allowadmin(self, ctx, userid: int, enable: str):
    """Bot owner only: register/unregister user as admin for this cog."""
    if self.bot.owner_ids is None or ctx.author.id not in self.bot.owner_ids:
        return await ctx.send("Only the bot owner can use this command.")
    enable = enable.lower()
    admins = await self.config.admins()
    if enable == "on":
        if userid not in admins:
            admins.append(userid)
            await ctx.send(f"User {userid} added as admin.")
        else:
            await ctx.send(f"User {userid} is already an admin.")
    elif enable == "off":
        if userid in admins:
            admins.remove(userid)
            await ctx.send(f"User {userid} removed from admins.")
        else:
            await ctx.send(f"User {userid} was not an admin.")
    else:
        await ctx.send("Enable must be 'on' or 'off'.")
        return
    await self.config.admins.set(admins)

    @commands.command()
    async def authme(self, ctx):
        """Admin command to get OAuth link for authorizing others."""
        if not await self.check_admin(ctx):
            return await ctx.send("You must be an admin to use this command.")
        url = await self.get_oauth_url(state=str(ctx.author.id))
        if url is None:
            return await ctx.send("OAuth2 Client ID or Secret is not set. Use authsetclientid and authsetsecret.")
        await ctx.send(f"Authorize here (admin): {url}")

    @commands.command()
    async def authoriseme(self, ctx):
        """Anyone can get OAuth link to authorize themselves."""
        url = await self.get_oauth_url(state=str(ctx.author.id))
        if url is None:
            await ctx.send("OAuth2 Client ID or Secret is not set. Please contact an admin.")
            return
        await ctx.send(f"Authorize yourself here: {url}")

    @commands.command()
    async def authforce(self, ctx, userid: int, server_id: int, loop: str = "no"):
        """Force add user to server, optionally loop to re-add if they leave."""
        if not await self.check_admin(ctx):
            return await ctx.send("You must be an admin to use this command.")
        loop_enabled = loop.lower() == "yes"
        forced = await self.config.forced_users()
        user_data = forced.get(str(userid), {"servers": [], "loop": False})

        if server_id not in user_data["servers"]:
            user_data["servers"].append(server_id)
        user_data["loop"] = loop_enabled
        forced[str(userid)] = user_data
        await self.config.forced_users.set(forced)

        guild = self.bot.get_guild(server_id)
        if not guild:
            return await ctx.send(f"Server ID {server_id} not found.")
        member = guild.get_member(userid)
        if member:
            await ctx.send(f"User {userid} is already in server {server_id}.")
        else:
            await ctx.send(f"User {userid} is not in server {server_id}. Cannot add automatically without OAuth token.")

        await ctx.send(f"User {userid} forced to server {server_id} with loop={loop_enabled}")

    @commands.command()
    async def authforceall(self, ctx, userid: int, enable: str):
        """Force add or remove user to/from all servers bot is in."""
        if not await self.check_admin(ctx):
            return await ctx.send("You must be an admin to use this command.")
        enable = enable.lower()
        forced = await self.config.forced_users()
        user_data = forced.get(str(userid), {"servers": [], "loop": False})

        if enable == "on":
            user_data["servers"] = [g.id for g in self.bot.guilds]
            user_data["loop"] = True
            forced[str(userid)] = user_data
            await ctx.send(f"User {userid} forced in all servers with looping enabled.")
        elif enable == "off":
            if str(userid) in forced:
                del forced[str(userid)]
            await ctx.send(f"User {userid} removed from forced list.")
        else:
            await ctx.send("Enable must be 'on' or 'off'.")
            return
        await self.config.forced_users.set(forced)

    @commands.command()
    async def checkemail(self, ctx, userid: int):
        """Check email of a user via stored OAuth info."""
        if not await self.check_admin(ctx):
            return await ctx.send("You must be an admin to use this command.")
        emails = await self.config.emails()
        email = emails.get(str(userid))
        if email:
            await ctx.send(f"User {userid} email: {email}")
        else:
            await ctx.send(f"No email stored for user {userid}.")

    @tasks.loop(minutes=5)
    async def loop_check_forced_users(self):
        forced = await self.config.forced_users()
        for user_id_str, data in forced.items():
            if not data.get("loop", False):
                continue
            user_id = int(user_id_str)
            for server_id in data.get("servers", []):
                guild = self.bot.get_guild(server_id)
                if not guild:
                    continue
                member = guild.get_member(user_id)
                if member is None:
                    owner = guild.owner
                    if owner:
                        try:
                            await owner.send(f"User {user_id} left {guild.name} but is forced to be there. Manual re-add required.")
                        except Exception:
                            pass

    @loop_check_forced_users.before_loop
    async def before_loop_check(self):
        await self.bot.wait_until_ready()
