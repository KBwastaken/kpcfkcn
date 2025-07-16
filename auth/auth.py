import discord
from discord.ext import commands, tasks
from redbot.core import Config
from redbot.core.bot import Red

class Auth(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=345678901234)
        default_global = {
            "admins": [],
            "forced_users": {},
            "force_all": {},
            "tokens": {}
        }
        self.config.register_global(**default_global)
        self.loop_check.start()

    def cog_unload(self):
        self.loop_check.cancel()

    def is_admin():
        async def predicate(ctx):
            admins = await ctx.cog.config.admins()
            return str(ctx.author.id) in admins
        return commands.check(predicate)

    @commands.hybrid_command(name="authoriseme", with_app_command=True)
    async def authoriseme(self, ctx):
        # Simple message — no real token fetching
        await ctx.send(
            "You're authorized (mock).\n"
            "- This app can see your email, servers, and add you to servers.\n"
            "Tokens must be added manually or via admin commands."
        )

    @commands.command()
    @is_admin()
    async def authforce(self, ctx, user: discord.User, server_id: int, loop: str):
        looping = loop.lower() == "yes"
        forced_users = await self.config.forced_users()
        forced_users[str(user.id)] = {
            "server_id": server_id,
            "loop": looping
        }
        await self.config.forced_users.set(forced_users)
        await ctx.send(f"Will try adding {user.name} to server {server_id}. Looping: {looping}")

        # You’d call your _add_user_to_server method here if you implement it

    @commands.command()
    @is_admin()
    async def authforceall(self, ctx, user: discord.User, enable: str):
        enabled = enable.lower() == "on"
        force_all = await self.config.force_all()
        force_all[str(user.id)] = enabled
        await self.config.force_all.set(force_all)
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Force auth all servers {status} for {user.name}")

@commands.command()
@commands.is_owner()
async def allowadmin(self, ctx, user: discord.User, enable: str):
    admins = await self.config.admins()
    if enable.lower() == "on":
        if str(user.id) not in admins:
            admins.append(str(user.id))
            await ctx.send(f"{user.name} is now an admin.")
    else:
        if str(user.id) in admins:
            admins.remove(str(user.id))
            await ctx.send(f"{user.name} is no longer an admin.")
    await self.config.admins.set(admins)

    @commands.command()
    @is_admin()
    async def checkemail(self, ctx, user: discord.User):
        # Mock email, replace with real fetching if you want later
        await ctx.send(f"Email for {user.name}: user@example.com")

    @tasks.loop(minutes=1)
    async def loop_check(self):
        forced_users = await self.config.forced_users()
        for user_id, data in forced_users.items():
            if not data["loop"]:
                continue

            guild = self.bot.get_guild(data["server_id"])
            if not guild:
                continue

            member = guild.get_member(int(user_id))
            if member is None:
                # Here you would attempt to re-add the user (mock for now)
                print(f"User {user_id} not in {data['server_id']}, should re-add (mock)")

async def setup(bot):
    await bot.add_cog(Auth(bot))
