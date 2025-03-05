import discord  
import logging  
from redbot.core import commands, Config  
from redbot.core.utils.predicates import MessagePredicate  

log = logging.getLogger("red.teamrole")  

class TeamRole(commands.Cog):  
    """Cog for creating and managing a team role across servers."""  

    def __init__(self, bot: commands.Bot):  
        self.bot = bot  
        self.config = Config.get_conf(self, identifier=123456789012345678)  
        # Global config will maintain a list of user IDs in the team.  
        self.config.register_global(team_members=[])  
        # Guild config stores the team role ID for that guild.  
        self.config.register_guild(team_role_id=None)  

    @commands.group()  
    async def team(self, ctx: commands.Context):  
        """Manage the KCN Team role and team database."""  
        if ctx.invoked_subcommand is None:  
            await ctx.send_help()  

    # • .team add <user>  
    @team.command(name="add")  
    async def team_add(self, ctx: commands.Context, user: discord.User):  
        """Add a user to the team database."""  
        async with self.config.team_members() as members:  
            if user.id in members:  
                return await ctx.send(f"{user.mention} is already in the team database.")  
            members.append(user.id)  
        await ctx.send(f"Added {user.mention} to the team database.")  

    # • .team remove <user>  
    @team.command(name="remove")  
    async def team_remove(self, ctx: commands.Context, user: discord.User):  
        """Remove a user from the team database."""  
        async with self.config.team_members() as members:  
            if user.id not in members:  
                return await ctx.send(f"{user.mention} is not in the team database.")  
            members.remove(user.id)  
        await ctx.send(f"Removed {user.mention} from the team database.")  

    async def create_team_role(self, guild: discord.Guild) -> discord.Role:  
        """  
        Create the 'KCN | Team' role in the guild with:  
          - Administrator permissions.  
          - Color #77bcd6.  
          - Position just under the bot’s highest role.  
        """  
        try:  
            role = discord.utils.get(guild.roles, name="KCN | Team")  
            if role is None:  
                role = await guild.create_role(  
                    name="KCN | Team",  
                    permissions=discord.Permissions(administrator=True),  
                    colour=discord.Colour(0x77bcd6),  
                    reason="Auto-created team role via .team setup"  
                )  
                # Move role to be just below the bot's top role.  
                bot_member = guild.get_member(self.bot.user.id)  
                if bot_member:  
                    # Ensure the bot has the necessary permissions to manage roles.  
                    if not bot_member.guild_permissions.manage_roles:  
                        log.error(f"Missing permissions to manage roles in {guild.name}")  
                        raise discord.Forbidden("Bot lacks permissions to manage roles.")  

                    # Get the bot's highest role in the guild.  
                    bot_roles = [role for role in guild.roles if role in bot_member.roles]  
                    if bot_roles:  
                        highest_bot_role = max(bot_roles, key=lambda r: r.position)  
                        # Position the team role just below the highest bot role.  
                        new_position = highest_bot_role.position - 1  
                        await role.edit(position=new_position)  
                    else:  
                        log.warning(f"Bot has no roles in {guild.name}")  
                else:  
                    log.error(f"Bot member not found in {guild.name}")  
            return role  
        except discord.Forbidden:  
            log.error(f"Forbidden error creating team role in {guild.name}")  
            raise  
        except Exception as e:  
            log.error(f"Failed to create team role in {guild.name}: {e}", exc_info=True)  
            raise  

    # • .team setup  
    @team.command(name="setup")  
    async def team_setup(self, ctx: commands.Context):  
        """Creates the KCN | Team role in this server."""  
        try:  
            role = await self.create_team_role(ctx.guild)  
            await self.config.guild(ctx.guild).team_role_id.set(role.id)  
            await ctx.send(f"Team role created: {role.mention}")  
        except discord.Forbidden:  
            await ctx.send("I don't have permission to create roles in this server.")  
        except Exception as e:  
            await ctx.send("Failed to create team role.")  
            log.error(f"Error during team role creation in guild '{ctx.guild.name}': {e}", exc_info=True)  

    # • .team update  
    @team.command(name="update")  
    async def team_update(self, ctx: commands.Context):  
        """  
        Iterate over all servers, ensuring the team role exists in each and  
        gives every user in the global team database the team role, and  
        positions it under the bot's highest role.  
        """  
        team_members = await self.config.team_members()  
        errors = []  
        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id()  
            if not role_id:  
                # If the role has not been created in this guild, create it.  
                try:  
                    role = await self.create_team_role(guild)  
                    await self.config.guild(guild).team_role_id.set(role.id)  
                except Exception as e:  
                    log.error(f"Error creating team role in {guild.name}: {e}", exc_info=True)  
                    errors.append(guild.name)  
                    continue  
            else:  
                role = guild.get_role(role_id)  
                if role is None:  
                    try:  
                        role = await self.create_team_role(guild)  
                        await self.config.guild(guild).team_role_id.set(role.id)  
                    except Exception as e:  
                        log.error(f"Role lookup/creation error in {guild.name}: {e}", exc_info=True)  
                        errors.append(guild.name)  
                        continue  

            # Ensure the role is positioned under the bot's highest role.  
            try:  
                bot_member = guild.get_member(self.bot.user.id)  
                if bot_member:  
                    bot_roles = [r for r in guild.roles if r in bot_member.roles]  
                    if bot_roles:  
                        highest_bot_role = max(bot_roles, key=lambda r: r.position)  
                        if role.position != highest_bot_role.position - 1:  
                            await role.edit(position=highest_bot_role.position - 1)  
                            log.info(f"Adjusted team role position in {guild.name}")  
                    else:  
                        log.warning(f"Bot has no roles in {guild.name}")  
                else:  
                    log.error(f"Bot member not found in {guild.name}")  
            except Exception as e:  
                log.error(f"Failed to adjust role position in {guild.name}: {e}")  

            # Add the role to each team member in this guild.  
            for user_id in team_members:  
                member = guild.get_member(user_id)  
                if member:  
                    try:  
                        if role not in member.roles:  
                            await member.add_roles(role, reason="Team update command")  
                    except Exception as e:  
                        log.error(f"Error adding team role to {member.display_name} in {guild.name}: {e}", exc_info=True)  
        msg = "Team update complete."  
        if errors:  
            msg += f" Errors in guilds: {', '.join(errors)}"  
        await ctx.send(msg)  

    # • .team delete  
    @team.command(name="delete")  
    async def team_delete(self, ctx: commands.Context):  
        """Removes the team role from THIS server only."""  
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

    # • .team wipe  
    @team.command(name="wipe")  
    async def team_wipe(self, ctx: commands.Context):  
        """  
        Removes all users from the global team database and deletes the team role  
        from every server.  
        """  
        pred = MessagePredicate.yes_or_no(ctx, "Are you sure you want to wipe ALL team data? (yes/no)")  
        try:  
            await self.bot.wait_for("message", check=pred, timeout=30)  
        except Exception:  
            return await ctx.send("Timed out, aborting wipe.")  
        if not pred.result:  
            return await ctx.send("Wipe aborted.")  

        # Wipe the global team database.  
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
                        log.error(f"Error deleting team role in {guild.name} during wipe: {e}", exc_info=True)  
                        errors.append(guild.name)  
                await self.config.guild(guild).team_role_id.clear()  
        msg = "Team data wiped."  
        if errors:  
            msg += f" Errors in guilds: {', '.join(errors)}"  
        await ctx.send(msg)  

# End of Cog
