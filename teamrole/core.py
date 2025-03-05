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

    @commands.Cog.listener()  
    async def on_guild_join(self, guild):  
        """Auto-create role when joining new server."""  
        try:  
            role = await create_team_role(guild, self.bot)  
            await self.config.guild(guild).team_role_id.set(role.id)  
        except Exception as e:  
            log.error(f"Role creation failed: {e}", exc_info=True)  

    @commands.group()  
    @commands.is_owner()  
    async def team(self, ctx):  
        """Manage team roles."""  
        # If no subcommand is given, you might choose to send help info.  
        if ctx.invoked_subcommand is None:  
            await ctx.send_help()  

    @team.command()  
    async def add(self, ctx, user: discord.User):  
        """Add user to global team."""  
        async with self.config.team_members() as members:  
            if user.id not in members:  
                members.append(user.id)  
                await ctx.send(f"Added {user.name} to team.")  
            else:  
                await ctx.send(f"{user.name} is already in team.")  

    @team.command()  
    async def remove(self, ctx, user: discord.User):  
        """Remove user from global team."""  
        async with self.config.team_members() as members:  
            if user.id in members:  
                members.remove(user.id)  
                await ctx.send(f"Removed {user.name} from team.")  
            else:  
                await ctx.send(f"{user.name} is not in team.")  

    @team.command()  
    async def update(self, ctx):  
        """Update roles in all servers."""  
        members = await self.config.team_members()  
        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id()  
            # If role_id is not set, create a new role and store its ID.  
            if role_id:  
                role = guild.get_role(role_id)  
            else:  
                role = await create_team_role(guild, self.bot)  
                await self.config.guild(guild).team_role_id.set(role.id)  
            # Add the role to every team member if they are in the guild.  
            for member_id in members:  
                if member := guild.get_member(member_id):  
                    await member.add_roles(role)  
        await ctx.send("Updated roles globally.")  

    @team.command()  
    async def delete(self, ctx):  
        """Delete the team role in the current server."""  
        # Using the MessagePredicate to confirm deletion. Adjust if needed.  
        if await MessagePredicate.yes_or_no(ctx, "Delete role? (yes/no)"):  
            role_id = await self.config.guild(ctx.guild).team_role_id()  
            if role_id:  
                role = ctx.guild.get_role(role_id)  
                if role:  
                    await role.delete(reason="TeamRole: delete command issued by owner")  
                    # Optionally reset the config for this guild.  
                    await self.config.guild(ctx.guild).team_role_id.clear()  
                    await ctx.send("Role deleted.")  
                else:  
                    await ctx.send("Role not found in this server.")  
            else:  
                await ctx.send("No team role set for this server.")  

    @team.command()  
    async def wipe(self, ctx):  
        """Wipe all team data."""  
        if await MessagePredicate.yes_or_no(ctx, "Wipe ALL data? (yes/no)"):  
            await self.config.team_members.set([])  
            for guild in self.bot.guilds:  
                role_id = await self.config.guild(guild).team_role_id()  
                if role_id:  
                    role = guild.get_role(role_id)  
                    if role:  
                        await role.delete(reason="TeamRole: wipe command issued by owner")  
                    await self.config.guild(guild).team_role_id.clear()  
            await ctx.send("All team data wiped.")
