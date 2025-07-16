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

    @tasks.loop(minutes=1)
    async def loop_check(self):
        # This runs every minute — replace with your real logic or leave empty
        forced_users = await self.config.forced_users()
        for user_id, data in forced_users.items():
            if not data.get("loop"):
                continue
            guild = self.bot.get_guild(data.get("server_id"))
            if not guild:
                continue
            member = guild.get_member(int(user_id))
            if member is None:
                # Here you would add the user back to the guild if looping is enabled
                # For now, just print a message (or remove this block)
                print(f"User {user_id} is not in guild {data.get('server_id')}, should re-add")

    def is_admin():
        async def predicate(ctx):
            admins = await ctx.cog.config.admins()
            return str(ctx.author.id) in admins
        return commands.check(predicate)

    @commands.hybrid_command(name="authoriseme", with_app_command=True)
    async def authoriseme(self, ctx):
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
        await ctx.send(f"Email for {user.name}: user@example.com")

async def setup(bot):
    await bot.add_cog(Auth(bot))
