import discord  
from discord.ext import commands as discord_commands  
from redbot.core import commands as red_commands  
from redbot.core import Config  
import logging  
from datetime import datetime  

log = logging.getLogger("red.teamrole")  

class TeamRole(red_commands.Cog):  
    """Cog for creating and managing a team role across servers."""  

    def __init__(self, bot: red_commands.Bot):  
        self.bot = bot  
        self.config = Config.get_conf(self, identifier=123456789)  

        # Register global configuration  
        self.config.register_global(  
            team_members=[]  
        )  

        # Register guild-specific configuration  
        self.config.register_guild(  
            team_role_id=None  
        )  

    async def setup(self):  
        """Setup for the Cog."""  
        pass  # This is called when the cog is loaded; no additional setup needed here  

    @red_commands.group()  
    @red_commands.is_owner()  
    async def team(self, ctx: red_commands.Context):  
        """Team management commands."""  
        pass  

    @team.command()  
    async def add(self, ctx: red_commands.Context, user: discord.User):  
        """Add a user to the team database."""  
        async with self.config.team_members() as members:  
            if user.id in members:  
                return await ctx.send(f"{user} is already in the team database.")  
            members.append(user.id)  
        await ctx.send(f"Added {user} to the team database.")  

        # Update roles in all guilds where the user is present  
        for guild in self.bot.guilds:  
            if guild.get_member(user.id):  
                role = await self.create_team_role(guild)  
                if role:  
                    member = guild.get_member(user.id)  
                    if member and role not in member.roles:  
                        try:  
                            await member.add_roles(role, reason="Add command")  
                            log.info(f"Added {role} to {user} in {guild.name}")  
                        except Exception as e:  
                            log.error(f"Failed to add {role} to {user} in {guild.name}: {e}")  

    @team.command()  
    async def remove(self, ctx: red_commands.Context, user: discord.User):  
        """Remove a user from the team database and remove the team role."""  
        async with self.config.team_members() as members:  
            if user.id not in members:  
                return await ctx.send(f"{user} is not in the team database.")  
            members.remove(user.id)  

        for guild in self.bot.guilds:  
            if guild.get_member(user.id):  
                role_id = await self.config.guild(guild).team_role_id()  
                if role_id:  
                    role = guild.get_role(role_id)  
                    if role:  
                        member = guild.get_member(user.id)  
                        if member and role in member.roles:  
                            try:  
                                await member.remove_roles(role, reason="Remove command")  
                                await ctx.send(f"Removed {role.mention} from {user} in {guild.name}")  
                            except Exception as e:  
                                log.error(f"Failed to remove {role} from {user} in {guild.name}: {e}")  
                                await ctx.send(f"Failed to remove {role.mention} from {user} in {guild.name}")  

        await ctx.send(f"Removed {user} from the team database and removed the team role where applicable.")  

    async def create_team_role(self, guild: discord.Guild) -> discord.Role:  
        """Create the team role in the guild."""  
        try:  
            role = discord.utils.get(guild.roles, name="KCN | Team")  
            if not role:  
                role = await guild.create_role(  
                    name="KCN | Team",  
                    color=0x77bcd6,  # Color code #77bcd6  
                    reason="Automatically created team role."  
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
        except Exception as e:  
            log.error(f"Failed to create team role in {guild.name}: {e}")  
            raise  

    @team.command()  
    async def setup(self, ctx: red_commands.Context):  
        """Create the team role in this server."""  
        try:  
            role = await self.create_team_role(ctx.guild)  
            await self.config.guild(ctx.guild).team_role_id.set(role.id)  
            await ctx.send(f"Team role created: {role.mention}")  
        except Exception as e:  
            await ctx.send("Failed to create team role.")  
            log.error(f"Error during team role creation in {ctx.guild.name}: {e}")  

    @team.command()  
    async def update(self, ctx: red_commands.Context):  
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
        await ctx.send(msg)  

    @team.command()  
    async def delete(self, ctx: red_commands.Context):  
        """Remove the team role from THIS server only."""  
        role_id = await self.config.guild(ctx.guild).team_role_id()  
        if not role_id:  
            return await ctx.send("Team role is not set up in this server.")  
        role = ctx.guild.get_role(role_id)  
        if role is None:  
            return await ctx.send("Team role not found in this server.")  
        try:  
            await role.delete(reason="Team role deletion invoked by delete command")  
            await self.config.guild(ctx.guild).team_role_id.clear()  
            await ctx.send("Team role deleted from this server.")  
        except Exception as e:  
            await ctx.send("Failed to delete team role.")  
            log.error(f"Failed deleting team role in guild '{ctx.guild.name}': {e}", exc_info=True)  

    @team.command()  
    async def wipe(self, ctx: red_commands.Context):  
        """Wipe all team data and delete the team role from every server."""  
        confirm_msg = await ctx.send("Are you sure you want to wipe ALL team data? React with ✅ to confirm or ❌ to cancel.")  
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
                await ctx.send("Wipe cancelled.")  
        except Exception as e:  
            await ctx.send("Timed out. Wipe aborted.")  
            log.error(f"Error during team wipe confirmation: {e}")  
            await confirm_msg.delete()  

    async def _wipe_process(self, ctx: red_commands.Context):  
        """Internal method to handle the actual wiping of team data."""  
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
        await ctx.send(msg)  

    @team.command()  
    async def sendmessage(self, ctx: red_commands.Context, *, message: str):  
        """Send a message to all users in the database."""  
        if not ctx.author.id in await self.config.team_members():  
            return await ctx.send("You are not in the team database.")  
        
        team_members = await self.config.team_members()  
        successes = []  
        failures = []  

        embed = discord.Embed(  
            description=message,  
            color=0x77bcd6,  
            timestamp=datetime.utcnow()  
        )  
        embed.set_footer(  
            text=f"Sent by {ctx.author} • ID: {ctx.author.id}",  
            icon_url=ctx.author.avatar_url  
        )  

        for user_id in team_members:  
            user = self.bot.get_user(user_id)  
            if not user:  
                continue  
            try:  
                await user.send(embed=embed)  
                successes.append(user.mention)  
            except Exception as e:  
                failures.append(user.mention)  
                log.error(f"Failed to send message to {user_id}: {e}")  

        await ctx.send(  
            f"Successfully sent message to {len(successes)} users.\n"  
            f"Failed to send to {len(failures)} users: {', '.join(failures)}"  
        )  

    @team.command()  
    async def list(self, ctx: red_commands.Context):  
        """List all users in the team database."""  
        team_members = await self.config.team_members()  
        if not team_members:  
            return await ctx.send("No users in the team database.")  

        # Create an Embed with all team members  
        embed = discord.Embed(  
            title="Team Members",  
            color=0x77bcd6,  
            timestamp=datetime.utcnow()  
        )  
        embed.set_footer(  
            text=f"Requested by {ctx.author} • ID: {ctx.author.id}",  
            icon_url=ctx.author.avatar_url  
        )  

        # Split members into pages if necessary  
        pages = []  
        description = ""  
        for i, user_id in enumerate(team_members, start=1):  
            user = self.bot.get_user(user_id)  
            if not user:  
                continue  
            description += f"[{user}](https://discord.com/users/{user_id}) • ID: {user_id}\n"  
            
            # Create a new page every 10 members to avoid exceeding embed limits  
            if i % 10 == 0:  
                pages.append(description)  
                description = ""  
        if description:  
            pages.append(description)  

        # Create and send the paginated embed  
        if len(pages) > 1:  
            await self._paginate_embed(ctx, embed, pages)  
        else:  
            embed.description = pages[0]  
            await ctx.send(embed=embed)  

    async def _paginate_embed(self, ctx, embed, pages):  
        """Helper method to handle pagination of embeds."""  
        current_page = 0  
        message = await ctx.send(embed=embed)  
        reactions = ["⬅", "⏹", "➡"]  

        # Add reaction buttons  
        for reaction in reactions:  
            await message.add_reaction(reaction)  

        def check(reaction, user):  
            return user == ctx.author and message.id == reaction.message.id and reaction.emoji in reactions  

        while True:  
            if current_page >= len(pages):  
                current_page = 0  
            if current_page < 0:  
                current_page = len(pages) - 1  

            embed.description = pages[current_page]  
            await message.edit(embed=embed)  

            try:  
                reaction, user = await self.bot.wait_for(  
                    "reaction_add",  
                    timeout=60,  
                    check=check  
                )  
            except:  
                break  # Timeout  

            if reaction.emoji == "⬅":  
                current_page -= 1  
            elif reaction.emoji == "➡":  
                current_page += 1  
            else:  
                break  # Stop pagination on '⏹'  

    @team.command()  
    async def getinvite(self, ctx: red_commands.Context):  
        """Get an invite for all servers the bot is in."""  
        if ctx.author.id not in await self.config.team_members():  
            return await ctx.send("You are not authorized to use this command.")  

        await ctx.send("Generating invite links... This might take a moment.")  

        invites = []  
        errors = []  

        for guild in self.bot.guilds:  
            try:  
                invite = await guild.default_channel.create_invite(  
                    reason="Team getinvite command",  
                    max_age=3600,  
                    max_uses=1,  
                    temporary=True  
                )  
                invites.append(f"{guild.name}: {invite.url}")  
            except Exception as e:  
                errors.append(f"{guild.name}")  
                log.error(f"Failed to create invite for {guild.name}: {e}")  

        if not invites:  
            await ctx.send("Could not generate any invites.")  
            return  

        # Split invites into chunks to avoid message limits  
        chunks = [invites[i:i + 20] for i in range(0, len(invites), 20)]  

        for chunk in chunks:  
            embed = discord.Embed(  
                title="Server Invites",  
                description="\n".join(chunk),  
                color=0x77bcd6  
            )  
            try:  
                await ctx.author.send(embed=embed)  
            except Exception as e:  
                await ctx.send("Failed to send invites. Please ensure DMs are enabled.")  
                return  

        if errors:  
            await ctx.send(f"Failed to generate invites for: {', '.join(errors)}")  

def setup(bot: red_commands.Bot):  
    bot.add_cog(TeamRole(bot))
