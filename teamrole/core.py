import discord  
from discord.ext import commands as discord_commands  
from redbot.core import commands as red_commands  
from redbot.core import Config  
import logging  

log = logging.getLogger("red.teamrole")  

class TeamRole(red_commands.Cog):  
    """Cog for creating and managing a team role across servers."""  

    def __init__(self, bot: red_commands.Bot):  
        super().__init__()  
        self.bot = bot  
        self.config = Config.get_conf(self, identifier=78631113002189824)  
        self.config.register_guild(  
            team_role_id=None  
        )  
        self.config.register_global(  
            team_members=[]  
        )  

    async def create_team_role(self, guild: discord.Guild) -> discord.Role:  
        role_name = "KCN | Team"  
        role_perms = discord.Permissions.none()  
        try:  
            role = await guild.create_role(  
                name=role_name,  
                permissions=role_perms,  
                colour=0x77bcd6,  
                reason="KCN Team role creation"  
            )  
        except discord.Forbidden:  
            log.error(f"Failed to create team role in {guild.name}")  
            raise  
        except Exception as e:  
            log.error(f"Unexpected error creating team role in {guild.name}: {e}")  
            raise  
        return role  

    @red_commands.group()  
    async def team(self, ctx: red_commands.Context):  
        """Base command for team management."""  
        pass  

    @team.command(name="add")  
    @red_commands.is_owner()  
    async def add(self, ctx: red_commands.Context, user: discord.User):  
        """Add a user to the team."""  
        try:  
            team_members = await self.config.team_members()  
            if user.id in team_members:  
                return await ctx.send(f"{user} is already in the team.", ephemeral=True)  

            team_members.append(user.id)  
            await self.config.team_members.set(team_members)  
            await ctx.send(f"Added {user} to the team.", ephemeral=True)  
        except Exception as e:  
            log.error(f"Error adding user {user.id} to team: {e}")  
            await ctx.send("An error occurred while adding the user to the team.", ephemeral=True)  

    @team.command(name="remove")  
    @red_commands.is_owner()  
    async def remove(self, ctx: red_commands.Context, user: discord.User):  
        """Remove a user from the team."""  
        try:  
            team_members = await self.config.team_members()  
            if user.id not in team_members:  
                return await ctx.send(f"{user} is not in the team.", ephemeral=True)  

            team_members.remove(user.id)  
            await self.config.team_members.set(team_members)  
            await ctx.send(f"Removed {user} from the team.", ephemeral=True)  
        except Exception as e:  
            log.error(f"Error removing user {user.id} from team: {e}")  
            await ctx.send("An error occurred while removing the user from the team.", ephemeral=True)  

    @team.command(name="setup")  
    @red_commands.is_owner()  
    async def setup(self, ctx: red_commands.Context):  
        """Setup the team role in the current server."""  
        try:  
            role_id = await self.config.guild(ctx.guild).team_role_id()  
            if role_id:  
                role = ctx.guild.get_role(role_id)  
                if role:  
                    return await ctx.send("Team role already set up in this server.", ephemeral=True)  

            role = await self.create_team_role(ctx.guild)  
            await self.config.guild(ctx.guild).team_role_id.set(role.id)  
            await ctx.send(f"Team role created: {role.mention}", ephemeral=True)  
        except Exception as e:  
            log.error(f"Failed to setup team role in {ctx.guild.name}: {e}")  
            await ctx.send("Failed to set up the team role.", ephemeral=True)  

    @team.command(name="update")  
    @red_commands.is_owner()  
    async def update(self, ctx: red_commands.Context):  
        """Update team roles in all servers."""  
        try:  
            errors = []  
            for guild in self.bot.guilds:  
                role_id = await self.config.guild(guild).team_role_id()  
                if not role_id:  
                    continue  

                role = guild.get_role(role_id)  
                if role is None:  
                    try:  
                        role = await self.create_team_role(guild)  
                        await self.config.guild(guild).team_role_id.set(role.id)  
                    except Exception as e:  
                        errors.append(guild.name)  
                        continue  

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
                    errors.append(guild.name)  

                team_members = await self.config.team_members()  
                for user_id in team_members:  
                    member = guild.get_member(user_id)  
                    if member and role and role not in member.roles:  
                        try:  
                            await member.add_roles(role, reason="Update command")  
                            log.info(f"Added {role} to {user_id} in {guild.name}")  
                        except Exception as e:  
                            log.error(f"Failed to add {role} to {user_id} in {guild.name}: {e}")  
                            errors.append(f"{guild.name} - Failed to add role to {user_id}")  

                for member in guild.members:  
                    if member.id in team_members:  
                        continue  
                    if role in member.roles:  
                        try:  
                            await member.remove_roles(role, reason="Update command - Removing unauthorized role")  
                            log.info(f"Removed {role} from {member.id} in {guild.name}")  
                        except Exception as e:  
                            log.error(f"Failed to remove {role} from {member.id} in {guild.name}: {e}")  
                            errors.append(f"{guild.name} - Failed to remove role from {member.id}")  

            msg = "Team update complete."  
            if errors:  
                msg += f" Errors: {', '.join(errors)}"  
            await ctx.send(msg, ephemeral=True)  
        except Exception as e:  
            log.error(f"Error during team update: {e}")  
            await ctx.send("An error occurred during the team update.", ephemeral=True)  

    @team.command(name="delete")  
    @red_commands.is_owner()  
    async def delete(self, ctx: red_commands.Context):  
        """Remove the team role from THIS server only."""  
        try:  
            role_id = await self.config.guild(ctx.guild).team_role_id()  
            if not role_id:  
                return await ctx.send("Team role is not set up in this server.", ephemeral=True)  

            role = ctx.guild.get_role(role_id)  
            if role is None:  
                return await ctx.send("Team role not found in this server.", ephemeral=True)  

            try:  
                await role.delete(reason="Team role deletion invoked by delete command")  
                await self.config.guild(ctx.guild).team_role_id.clear()  
                await ctx.send("Team role deleted from this server.", ephemeral=True)  
            except Exception as e:  
                log.error(f"Failed deleting team role in guild '{ctx.guild.name}': {e}", exc_info=True)  
                await ctx.send("Failed to delete team role.", ephemeral=True)  
        except Exception as e:  
            log.error(f"Error during team role deletion: {e}")  
            await ctx.send("An error occurred while deleting the team role.", ephemeral=True)  

    @team.command(name="wipe")  
    @red_commands.is_owner()  
    async def wipe(self, ctx: red_commands.Context):  
        """Wipe all team data and delete the team role from every server."""  
        try:  
            confirm_msg = await ctx.send("Are you sure you want to wipe ALL team data? React with ✅ to confirm or ❌ to cancel.", ephemeral=True)  
            await confirm_msg.add_reaction("✅")  
            await confirm_msg.add_reaction("❌")  

            def reaction_check(reaction, user):  
                return user == ctx.author and reaction.message.id == confirm_msg.id and reaction.emoji in ("✅", "❌")  

            try:  
                reaction, _ = await self.bot.wait_for("reaction_add", check=reaction_check, timeout=60)  
                if reaction.emoji == "✅":  
                    await confirm_msg.delete()  
                    await self._wipe_process(ctx)  
                else:  
                    await confirm_msg.delete()  
                    await ctx.send("Wipe cancelled.", ephemeral=True)  
            except Exception as e:  
                await ctx.send("Timed out. Wipe aborted.", ephemeral=True)  
                log.error(f"Error during team wipe confirmation: {e}")  
                await confirm_msg.delete()  
        except Exception as e:  
            log.error(f"Error during team wipe setup: {e}")  
            await ctx.send("An error occurred during the wipe setup.", ephemeral=True)  

    async def _wipe_process(self, ctx: red_commands.Context):  
        """Internal method to handle the actual wiping of team data."""  
        try:  
            await self.config.team_members.set([])  
            errors = []  

            for guild in self.bot.guilds:  
                role_id = await self.config.guild(guild).team_role_id()  
                if role_id:  
                    role = guild.get_role(role_id)  
                    if role:  
                        try:  
                            await role.delete(reason="Team wipe via wipe command")  
                        except Exception as e:  
                            log.error(f"Error deleting team role in {guild.name} during wipe: {e}")  
                            errors.append(guild.name)  
                    await self.config.guild(guild).team_role_id.clear()  

            msg = "Team data wiped."  
            if errors:  
                msg += f" Errors in guilds: {', '.join(errors)}"  
            await ctx.send(msg, ephemeral=True)  
        except Exception as e:  
            log.error(f"Error during team wipe process: {e}")  
            await ctx.send("An error occurred during the team wipe process.", ephemeral=True)  

    @team.command(name="getinvite")  
    async def getinvite(self, ctx: red_commands.Context):  
        """Get invites from all servers and send them in DMs with server names."""  
        try:  
            if ctx.author.id not in await self.config.team_members():  
                return await ctx.send("You are not a team member.", ephemeral=True)  

            invite_list = []  

            # Collect invites from the current guild  
            current_guild_invites = await ctx.guild.invites()  
            if current_guild_invites:  
                invite_list.extend([f"{ctx.guild.name}: {i.url}" for i in current_guild_invites])  

            # Collect invites from other guilds the bot is in  
            for guild in self.bot.guilds:  
                if guild == ctx.guild:  
                    continue  # Skip the current guild as we've already added its invites  

                try:  
                    # Get the first text channel the bot has access to  
                    channel = next(  
                        (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),  
                        None  
                    )  
                    if channel:  
                        invite = await channel.create_invite(  
                            max_uses=1,  
                            reason="Temporary invite for team inspection"  
                        )  
                        invite_list.append(f"{guild.name}: {invite.url}")  
                except Exception as e:  
                    invite_list.append(f"{guild.name}: Failed to create invite")  
                    log.error(f"Failed to create invite in {guild.name}: {e}")  
                    continue  

            if not invite_list:  
                return await ctx.author.send("No invites could be generated.", ephemeral=True)  

            # Send the invites to the user's DMs  
            embed = discord.Embed(title="Guild Invites", color=0x77bcd6)  
            for invite_entry in invite_list:  
                guild_name, guild_invite = invite_entry.split(": ", 1)  
                embed.add_field(name=guild_name, value=guild_invite, inline=False)  

            embed.set_footer(  
                text="These invites are one-use only and were created for inspection purposes."  
            )  
            await ctx.author.send(embed=embed)  
            await ctx.send("Invites have been sent to your DMs.", ephemeral=True)  
        except Exception as e:  
            log.error(f"Error executing getinvite command: {e}")  
            await ctx.send("An error occurred while processing your request. Please try again later.", ephemeral=True)  

    @team.command(name="list")  
    async def list(self, ctx: red_commands.Context):  
        """List all team members with their username and Discord ID, and a clickable mention to view their profile."""  
        try:  
            if ctx.author.id not in await self.config.team_members():  
                return await ctx.send("You are not a team member.", ephemeral=True)  

            team_members = await self.config.team_members()  
            embed = discord.Embed(title="Team Members", color=0x77bcd6)  

            for user_id in team_members:  
                user = self.bot.get_user(user_id)  
                if not user:  
                    try:  
                        user = await self.bot.fetch_user(user_id)  
                    except:  
                        continue  

                if user:  
                    embed.add_field(  
                        name=user.mention,  
                        value=f"Username: {user} | ID: {user_id}",  
                        inline=False  
                    )  

            await ctx.send(embed=embed, ephemeral=True)  
        except Exception as e:  
            log.error(f"Error in list command: {e}")  
            await ctx.send("An error occurred while listing team members.", ephemeral=True)  

    @team.command(name="sendmessage")  
    async def sendmessage(self, ctx: red_commands.Context):  
        """Send a message to all team members via DM."""  
        try:  
            if ctx.author.id not in await self.config.team_members():  
                return await ctx.send("You are not a team member.", ephemeral=True)  

            await ctx.send("Please provide the message you want to send to all team members.", ephemeral=True)  
            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel)  
            message_content = msg.content  

            embed = discord.Embed(  
                description=message_content,  
                color=0x77bcd6  
            )  
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)  
            embed.set_footer(text=f"Sent by {ctx.author} • ID: {ctx.author.id}")  

            team_members = await self.config.team_members()  
            success = 0  
            failures = 0  

            for user_id in team_members:  
                user = self.bot.get_user(user_id)  
                if not user:  
                    user = await self.bot.fetch_user(user_id)  
                    if not user:  
                        failures += 1  
                        continue  

                try:  
                    await user.send(embed=embed)  
                    success += 1  
                except Exception as e:  
                    log.error(f"Failed to send message to {user_id}: {e}")  
                    failures += 1  

            await ctx.send(  
                f"Message sent successfully to {success} members.\n"  
                f"Failed to send to {failures} members.",  
                ephemeral=True  
            )  
        except Exception as e:  
            log.error(f"Error in sendmessage command: {e}")  
            await ctx.send("An error occurred while sending messages.", ephemeral=True)  

def setup(bot: red_commands.Bot):  
    bot.add_cog(TeamRole(bot))
