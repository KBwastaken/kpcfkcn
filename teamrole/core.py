import discord  
from discord.ext import commands as discord_commands  
from redbot.core import commands as red_commands  
from redbot.core import Config  
from discord.ext import commands  
import logging  
from datetime import datetime  
import datetime  

log = logging.getLogger("red.teamrole")  
log = logging.getLogger('red')  

class TeamRole(red_commands.Cog):  
    """Cog for creating and managing a team role across servers."""  

    def __init__(self, bot: red_commands.Bot):  
class TeamRole(commands.RedBase):  
    def __init__(self, bot):  
        super().__init__()  
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
    @commands.group()  
    async def team(self, ctx: commands.Context):  
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
    async def create(self, ctx: commands.Context):  
        """Create team role in this server."""  
        role_name = "Team"  
        role = discord.utils.get(ctx.guild.roles, name=role_name)  
        if role:  
            return await ctx.send("Team role already exists.")  

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
            role = await ctx.guild.create_role(  
                name=role_name,  
                colour=discord.Colour(0x77bcd6),  
                reason="Team role creation"  
            )  
            await self.config.guild(ctx.guild).team_role_id.set(role.id)  
            await ctx.send(f"Team role created: {role.mention}")  
            log.info(f"Team role created in {ctx.guild.name}")  
        except Exception as e:  
            await ctx.send("Failed to create team role.")  
            log.error(f"Error during team role creation in {ctx.guild.name}: {e}")  

    @team.command()  
    async def update(self, ctx: red_commands.Context):  
    async def update(self, ctx: commands.Context):  
        """Update team roles across all servers to match the database."""  
        team_members = await self.config.team_members()  
        errors = []  

        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id()  
            role_id = await self.config.guild(guild).team_role_id.get()  
            if not role_id:  
                try:  
                    role = await self.create_team_role(guild)  
@@ -179,7 +98,7 @@ async def update(self, ctx: red_commands.Context):
        await ctx.send(msg)  

    @team.command()  
    async def delete(self, ctx: red_commands.Context):  
    async def delete(self, ctx: commands.Context):  
        """Remove the team role from THIS server only."""  
        role_id = await self.config.guild(ctx.guild).team_role_id()  
        if not role_id:  
@@ -196,9 +115,9 @@ async def delete(self, ctx: red_commands.Context):
            log.error(f"Failed deleting team role in guild '{ctx.guild.name}': {e}", exc_info=True)  

    @team.command()  
    async def wipe(self, ctx: red_commands.Context):  
    async def wipe(self, ctx: commands.Context):  
        """Wipe all team data and delete the team role from every server."""  
        confirm_msg = await ctx.send("Are you sure you want to wipe ALL team data? React with ✅ to confirm or ❌ to cancel.")  
        confirm_msg = await ctx.send("Is you sure you want to wipe ALL team data? React with ✅ to confirm or ❌ to cancel.")  
        await confirm_msg.add_reaction("✅")  
        await confirm_msg.add_reaction("❌")  

@@ -211,14 +130,14 @@ def reaction_check(reaction, user):
                await confirm_msg.delete()  
                await self._wipe_process(ctx)  
            else:  
                await confirm_msg.delete()  
                await ctx.send("Wipe cancelled.")  
                    await confirm_msg.delete()  
                    await ctx.send("Wipe canceled.")  
        except Exception as e:  
            await ctx.send("Timed out. Wipe aborted.")  
            log.error(f"Error during team wipe confirmation: {e}")  
            await confirm_msg.delete()  

    async def _wipe_process(self, ctx: red_commands.Context):  
    async def _wipe_process(self, ctx: commands.Context):  
        """Internal method to handle the actual wiping of team data."""  
        await self.config.team_members.set([])  
        errors = []  
@@ -229,21 +148,21 @@ async def _wipe_process(self, ctx: red_commands.Context):
                role = guild.get_role(role_id)  
                if role:  
                    try:  
                        await role.delete(reason="Team wipe via wipe command")  
                        await role.delete(reason="Team role deletion during wipe")  
                        await self.config.guild(guild).team_role_id.clear()  
                    except Exception as e:  
                        log.error(f"Error deleting team role in {guild.name} during wipe: {e}")  
                        log.error(f"Error deleting team role in {guild.name}: {e}")  
                        errors.append(guild.name)  
                await self.config.guild(guild).team_role_id.clear()  

        msg = "Team data wiped."  
        if errors:  
            msg += f" Errors in guilds: {', '.join(errors)}"  
            msg += f" Errors occurred in guilds: {', '.join(errors)}"  
        await ctx.send(msg)  

    @team.command()  
    async def sendmessage(self, ctx: red_commands.Context, *, message: str):  
    async def sendmessage(self, ctx: commands.Context, *, message: str):  
        """Send a message to all users in the database."""  
        if not ctx.author.id in await self.config.team_members():  
        if ctx.author.id not in await self.config.team_members():  
            return await ctx.send("You are not in the team database.")  

        team_members = await self.config.team_members()  
@@ -253,7 +172,7 @@ async def sendmessage(self, ctx: red_commands.Context, *, message: str):
        embed = discord.Embed(  
            description=message,  
            color=0x77bcd6,  
            timestamp=datetime.utcnow()  
            timestamp=datetime.datetime.utcnow()  
        )  
        embed.set_footer(  
            text=f"Sent by {ctx.author} • ID: {ctx.author.id}",  
@@ -266,9 +185,9 @@ async def sendmessage(self, ctx: red_commands.Context, *, message: str):
                continue  
            try:  
                await user.send(embed=embed)  
                successes.append(user.mention)  
                successes.append(str(user))  
            except Exception as e:  
                failures.append(user.mention)  
                failures.append(str(user))  
                log.error(f"Failed to send message to {user_id}: {e}")  

        await ctx.send(  
@@ -277,7 +196,7 @@ async def sendmessage(self, ctx: red_commands.Context, *, message: str):
        )  

    @team.command()  
    async def list(self, ctx: red_commands.Context):  
    async def list(self, ctx: commands.Context):  
        """List all users in the team database."""  
        team_members = await self.config.team_members()  
        if not team_members:  
@@ -287,21 +206,21 @@ async def list(self, ctx: red_commands.Context):
        embed = discord.Embed(  
            title="Team Members",  
            color=0x77bcd6,  
            timestamp=datetime.utcnow()  
            timestamp=datetime.datetime.utcnow()  
        )  
        embed.set_footer(  
            text=f"Requested by {ctx.author} • ID: {ctx.author.id}",  
            icon_url=ctx.author.avatar_url  
        )  

        # Split members into pages if necessary  
        pages = []  
        description = ""  
        for i, user_id in enumerate(team_members, start=1):  
        pages = []  
        for i, user_id in enumerate(team_members, 1):  
            user = self.bot.get_user(user_id)  
            if not user:  
            if user is None:  
                continue  
            description += f"[{user}](https://discord.com/users/{user_id}) • ID: {user_id}\n"  
            description += f"[{user}]({f'https://discord.com/users/{user_id}'}•ID:{user_id})\n"  

            # Create a new page every 10 members to avoid exceeding embed limits  
            if i % 10 == 0:  
@@ -314,7 +233,8 @@ async def list(self, ctx: red_commands.Context):
        if len(pages) > 1:  
            await self._paginate_embed(ctx, embed, pages)  
        else:  
            embed.description = pages[0]  
            if description:  
                embed.description = description  
            await ctx.send(embed=embed)  

    async def _paginate_embed(self, ctx, embed, pages):  
@@ -327,8 +247,12 @@ async def _paginate_embed(self, ctx, embed, pages):
        for reaction in reactions:  
            await message.add_reaction(reaction)  

        def check(reaction, user):  
            return user == ctx.author and message.id == reaction.message.id and reaction.emoji in reactions  
        def reaction_check(reaction, user):  
            return (  
                user == ctx.author and   
                message.id == reaction.message.id and   
                reaction.emoji in reactions  
            )  

        while True:  
            if current_page >= len(pages):  
@@ -343,9 +267,9 @@ def check(reaction, user):
                reaction, user = await self.bot.wait_for(  
                    "reaction_add",  
                    timeout=60,  
                    check=check  
                    check=reaction_check  
                )  
            except:  
            except asyncio.TimeoutError:  
                break  # Timeout  

            if reaction.emoji == "⬅":  
@@ -356,7 +280,7 @@ def check(reaction, user):
                break  # Stop pagination on '⏹'  

    @team.command()  
    async def getinvite(self, ctx: red_commands.Context):  
    async def getinvite(self, ctx: commands.Context):  
        """Get an invite for all servers the bot is in."""  
        if ctx.author.id not in await self.config.team_members():  
            return await ctx.send("You are not authorized to use this command.")  
@@ -367,23 +291,30 @@ async def getinvite(self, ctx: red_commands.Context):
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
            # Retrieve all text channels and sort by position to find the first channel  
            text_channels = sorted(guild.text_channels, key=lambda x: x.position)  
            if text_channels:  
                default_channel = text_channels[0]  
                try:  
                    invite = await default_channel.create_invite(  
                        reason="Team getinvite command",  
                        max_age=3600,  
                        max_uses=1,  
                        temporary=True  
                    )  
                    invites.append(f"{guild.name}: {invite.url}")  
                except Exception as e:  
                    errors.append(f"{guild.name}")  
                    log.error(f"Failed to create invite for {guild.name}: {e}")  
            else:  
                errors.append(f"{guild.name}")  
                log.error(f"Failed to create invite for {guild.name}: {e}")  
                log.error(f"No text channels found in {guild.name}")  

        if not invites:  
            await ctx.send("Could not generate any invites.")  
            return  

        # Split invites into chunks to avoid message limits  
        # Split invites into chunks of 20 to avoid exceeding message limits  
        chunks = [invites[i:i + 20] for i in range(0, len(invites), 20)]  

        for chunk in chunks:  
@@ -395,11 +326,11 @@ async def getinvite(self, ctx: red_commands.Context):
            try:  
                await ctx.author.send(embed=embed)  
            except Exception as e:  
                await ctx.send("Failed to send invites. Please ensure DMs are enabled.")  
                await ctx.send("Failed to send invites. Please ensure direct messages are enabled.")  
                return  

        if errors:  
            await ctx.send(f"Failed to generate invites for: {', '.join(errors)}")  

def setup(bot: red_commands.Bot):  
def setup(bot):  
    bot.add_cog(TeamRole(bot))
