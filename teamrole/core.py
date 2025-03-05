import discord
import logging
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate

from .utils import create_team_role

log = logging.getLogger("red.teamrole")

class TeamRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(team_members=[])
        self.config.register_guild(team_role_id=None)

    async def is_bot_owner(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            role = await create_team_role(guild, self.bot)
            await self.config.guild(guild).team_role_id.set(role.id)
            log.info(f"Created 'KCN | Team' role in {guild.name}")
        except Exception as e:
            log.error(f"Role creation failed: {e}")

    @commands.group()
    async def team(self, ctx):
        """Team role management"""
        if not await self.is_bot_owner(ctx):
            return await ctx.send("❌ You need bot owner permissions.")

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add user to global team"""
        async with self.config.team_members() as members:
            if user.id not in members:
                members.append(user.id)
                await ctx.send(f"✅ Added {user.name} to team")
            else:
                await ctx.send(f"⚠️ {user.name} is already in team")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove user from global team"""
        async with self.config.team_members() as members:
            if user.id in members:
                members.remove(user.id)
                await ctx.send(f"✅ Removed {user.name} from team")
            else:
                await ctx.send(f"⚠️ {user.name} not in team")

    @team.command()
    async def update(self, ctx):
        """Update roles across all servers"""
        members = await self.config.team_members()
        for guild in self.bot.guilds:
            role = await create_team_role(guild, self.bot)
            for member_id in members:
                member = guild.get_member(member_id)
                if member and role not in member.roles:
                    await member.add_roles(role)
        await ctx.send("✅ Updated roles globally")

    @team.command()
    async def delete(self, ctx):
        """Delete role in current server"""
        role_id = await self.config.guild(ctx.guild).team_role_id()
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                await role.delete()
                await ctx.send("✅ Role deleted")
                return
        await ctx.send("❌ No role exists here")

    @team.command()
    async def wipe(self, ctx):
        """Wipe all team data"""
        await self.config.team_members.set([])
        for guild in self.bot.guilds:
            role_id = await self.config.guild(guild).team_role_id()
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    await role.delete()
        await ctx.send("✅ Wiped all team data")
