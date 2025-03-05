import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from .utils import create_team_role, reorder_role

class TeamRole(commands.Cog):
    """Global Team Role Management"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(team_members=[])

    def format_username(self, user: discord.User) -> str:
        """Formats a username, including discriminator if available"""
        return f"{user.name}#{user.discriminator}" if user.discriminator else user.name

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Creates the role when bot joins a new server"""
        await create_team_role(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Assigns the role to registered team members when they join"""
        team_members = await self.config.team_members()
        if member.id in team_members:
            role = await create_team_role(member.guild)
            if role:
                await member.add_roles(role, reason="User is part of the KCN Team")

    @commands.group()
    @checks.admin_or_permissions(administrator=True)
    async def team(self, ctx: commands.Context):
        """Manage the global team role"""
        pass

    @team.command(name="add")
    async def team_add(self, ctx: commands.Context, user: discord.User):
        """Add a user to the global team"""
        async with self.config.team_members() as team_members:
            if user.id not in team_members:
                team_members.append(user.id)

        # Assign the role in every guild
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member:
                role = await create_team_role(guild)
                if role:
                    await member.add_roles(role, reason="Added to KCN Team")

        await ctx.send(f"✅ **{self.format_username(user)}** has been added to the team.")

    @team.command(name="remove")
    async def team_remove(self, ctx: commands.Context, user: discord.User):
        """Remove a user from the global team"""
        async with self.config.team_members() as team_members:
            if user.id in team_members:
                team_members.remove(user.id)

        # Remove the role in every guild
        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member:
                role = discord.utils.get(guild.roles, name="KCN | Team")
                if role:
                    await member.remove_roles(role, reason="Removed from KCN Team")

        await ctx.send(f"✅ **{self.format_username(user)}** has been removed from the team.")

    @team.command(name="update")
    async def team_update(self, ctx: commands.Context):
        """Reapply the team role to all registered users across all servers"""
        team_members = await self.config.team_members()
        updated_servers = 0

        for guild in self.bot.guilds:
            role = await create_team_role(guild)
            if not role:
                continue

            for user_id in team_members:
                member = guild.get_member(user_id)
                if member and role not in member.roles:
                    await member.add_roles(role, reason="Team role update")

            updated_servers += 1

        await ctx.send(f"✅ Team role updated in {updated_servers} servers.")
