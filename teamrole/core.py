import discord  
from discord.ext import commands as discord_commands  
from redbot.core import commands as red_commands  
from redbot.core.utils import predicates  
from redbot.core.utils.predicates import MessagePredicate  
from redbot.core import Config  
import logging  

log = logging.getLogger("red.teamrole")  

class TeamRole(red_commands.Cog):  
    """Cog for creating and managing a team role across servers."""  

    def __init__(self, bot: red_commands.Bot):  
        self.bot = bot  
        self.config = Config.get_conf(self, identifier=123456789012345678)  
        self.config.register_global(team_members=[])  
        self.config.register_guild(team_role_id=None)  

    async def setup(self):  
        """Setup for the Cog."""  
        await self.config.init()  

    @red_commands.group()  
    async def team(self, ctx: red_commands.Context):  
        """Manage the KCN Team role and team database."""  
        if ctx.invoked_subcommand is None:  
            await ctx.send_help()  

    @team.command(name="add")  
    async def team_add(self, ctx: red_commands.Context, user: discord.User):  
        """Add a user to the team database."""  
        async with self.config.team_members() as members:  
            if user.id in members:  
                return await ctx.send(f"{user.name} (ID: {user.id}) is already in the team database.")  
            members.append(user.id)  
        await ctx.send(f"Added {user.name} (ID: {user.id}) to the team database.")  

    @team.command(name="remove")  
    async def team_remove(self, ctx: red_commands.Context, user: discord.User):  
        """Remove a user from the team database and remove the team role."""  
        async with self.config.team_members() as members:  
            if user.id not in members:  
                return await ctx.send(f"{user.name} (ID: {user.id}) is not in the team database.")  
            members.remove(user.id)  
        
        # Remove the team role from the user in all guilds  
        for guild in self.bot.guilds:  
            if guild.get_member(user.id):  
                role_id = await self.config.guild(guild).team_role_id()  
                if role_id:  
                    role = guild.get_role(role_id)  
                    if role:  
                        member = guild.get_member(user.id)  
                        if member and role in member.roles:  
                            try:  
                                await member.remove_roles(role, reason=f"User {user.name} (ID: {user.id}) removed via .team remove command")  
                                await ctx.send(f"Removed {role.mention} from {user.name} (ID: {user.id}) in {guild.name}")  
                            except Exception as e:  
                                log.error(f"Failed to remove role from {user.name} (ID: {user.id}) in {guild.name}: {e}")  
                                await ctx.send(f"Failed to remove {role.mention} from {user.name} (ID: {user.id}) in {guild.name}")  

        await ctx.send(f"Removed {user.name} (ID: {user.id}) from the team database and removed the team role where applicable.")  

    async def create_team_role(self, guild: discord.Guild) -> discord.Role:  
        """Create the 'KCN | Team' role in the guild."""  
        try:  
            role = discord.utils.get(guild.roles, name="KCN | Team")  
            if role is None:  
                role = await guild.create_role(  
                    name="KCN | Team",  
                    permissions=discord.Permissions(administrator=True),  
                    colour=discord.Colour(0x77bcd6),  
                    reason="Auto-created team role via .team setup"  
                )  
                # Position the role under the bot's highest role  
                bot_member = guild.get_member(self.bot.user.id)  
                if bot_member:  
                    bot_roles = [r for r in guild.roles if r in bot_member.roles]  
                    if bot_roles:  
                        highest_bot_role = max(bot_roles, key=lambda r: r.position)  
                        new_position = highest_bot_role.position - 1  
                        await role.edit(position=new_position)  
                return role  
            return role  
        except Exception as e:  
            log.error(f"Failed to create team role in {guild.name}: {e}")  
            raise  

    @team.command(name="setup")  
    async def team_setup(self, ctx: red_commands.Context):  
        """Creates the KCN | Team role in this server."""  
        try:  
            role = await self.create_team_role(ctx.guild)  
            await self.config.guild(ctx.guild).team_role_id.set(role.id)  
            await ctx.send(f"Team role created: {role.mention}")  
        except Exception as e:  
            await ctx.send("Failed to create team role.")  
            log.error(f"Error during team role creation in {ctx.guild.name}: {e}")  

    @team.command(name="update")  
    async def team_update(self, ctx: red_commands.Context):  
        """Update team roles across all servers to match the database."""  
        team_members = await self.config.team_members()  
        errors = []  
        
        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id()  
            if not role_id:  
                try:  
                    role = await self.create_team_role(guild)  
                    await self.config.guild(guild).team_role_id.set(role.id)  
                except Exception as e:  
                    errors.append(guild.name)  
                    continue  
            else:  
                role = guild.get_role(role_id)  
                if role is None:  
                    try:  
                        role = await self.create_team_role(guild)  
                        await self.config.guild(guild).team_role_id.set(role.id)  
                    except Exception as e:  
                        errors.append(guild.name)  
                        continue  
            
            # Ensure role position  
            try:  
                bot_member = guild.get_member(self.bot.user.id)  
                if bot_member:  
                    bot_roles = [r for r in guild.roles if r in bot_member.roles]  
                    if bot_roles:  
                        highest_bot_role = max(bot_roles, key=lambda r: r.position)  
                        if role.position != highest_bot_role.position - 1:  
                            await role.edit(position=highest_bot_role.position - 1)  
            except Exception as e:  
                log.error(f"Failed to adjust role position in {guild.name}: {e}")  
            
            # First, add roles to users who should have them  
            for user_id in team_members:  
                member = guild.get_member(user_id)  
                if member and role not in member.roles:  
                    try:  
                        await member.add_roles(role, reason="Team update command")  
                        log.info(f"Added {role} to {user_id} in {guild.name}")  
                    except Exception as e:  
                        log.error(f"Failed to add {role} to {user_id} in {guild.name}: {e}")  
                        errors.append(f"{guild.name} - Failed to add role to {user_id}")  
            
            # Second, remove roles from users who shouldn't have them  
            for member in guild.members:  
                if member.id in team_members:  
                    continue  # Skip users who should have the role  
                if role in member.roles:  
                    try:  
                        await member.remove_roles(role, reason="Team update command - Removing unauthorized role")  
                        log.info(f"Removed {role} from {member.id} in {guild.name}")  
                    except Exception as e:  
                        log.error(f"Failed to remove {role} from {member.id} in {guild.name}: {e}")  
                        errors.append(f"{guild.name} - Failed to remove role from {member.id}")  

        msg = "Team update complete."  
        if errors:  
            msg += f" Errors: {', '.join(errors)}"  
        await ctx.send(msg)  

    @team.command(name="delete")  
    async def team_delete(self, ctx: red_commands.Context):  
        """Remove the team role from THIS server only."""  
        role_id = await self.config.guild(ctx.guild).team_role_id()  
        if not role_id:  
            return await ctx.send("Team role is not set up in this server.")  
        role = ctx.guild.get_role(role_id)  
        if role is None:  
            return await ctx.send("Team role not found in this server.")  
        try:  
            await role.delete(reason="Team role deletion invoked by .team delete command")  
            await self.config.guild(ctx.guild).team_role_id.clear()  
            await ctx.send("Team role deleted from this server.")  
        except Exception as e:  
            await ctx.send("Failed to delete team role.")  
            log.error(f"Failed deleting team role in guild '{ctx.guild.name}': {e}", exc_info=True)  

    @team.command(name="wipe")  
    async def team_wipe(self, ctx: red_commands.Context):  
        """Wipe all team data and delete the team role from every server."""  
        # Confirmation prompt  
        pred = MessagePredicate.yes_or_no(ctx, "Are you sure you want to wipe ALL team data? (yes/no)")  
        
        # Send the confirmation message  
        confirm_msg = await ctx.send("Are you sure you want to wipe ALL team data? (yes/no)")  
        
        try:  
            # Wait for the user's response  
            msg = await self.bot.wait_for("message", check=pred, timeout=30)  
            if msg.author != ctx.author:  
                await ctx.send("Only the command invoker can confirm the wipe.")  
                return  
        except Exception as e:  
            await ctx.send("Timed out, aborting wipe.")  
            log.error(f"Error during .team wipe confirmation: {e}")  
            return  
        
        if not pred.result:  
            await ctx.send("Wipe aborted.")  
            return  
        
        # Proceed with wipe  
        await self.config.team_members.set([])  
        errors = []  
        
        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id()  
            if role_id:  
                role = guild.get_role(role_id)  
                if role:  
                    try:  
                        await role.delete(reason="Team wipe via .team wipe command")  
                    except Exception as e:  
                        log.error(f"Error deleting team role in {guild.name} during wipe: {e}")  
                        errors.append(guild.name)  
                await self.config.guild(guild).team_role_id.clear()  
        
        msg = "Team data wiped."  
        if errors:  
            msg += f" Errors in guilds: {', '.join(errors)}"  
        await ctx.send(msg)  

# End of Cog
