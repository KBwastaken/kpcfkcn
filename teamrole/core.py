# team/team.py
import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.chat_formatting import box

class TeamCommands(commands.Cog):
    """Team management cog for KCN"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(team_members=[])
        self.config.register_guild(team_role=None)

    @commands.group()
    @commands.is_owner()
    async def team(self, ctx):
        """Team management commands"""
        pass

    @team.command()
    async def setup(self, ctx):
        """Setup the team role in this server"""
        guild = ctx.guild
        bot_member = guild.me
        bot_top_role = bot_member.top_role
        
        # Create role with admin permissions
        role = await guild.create_role(
            name="KCN | Team",
            permissions=discord.Permissions(administrator=True),
            color=discord.Color.from_str("#77bcd6"),
            reason="Team role setup"
        )
        
        # Position role below bot's top role
        try:
            await role.edit(position=bot_top_role.position - 1)
        except discord.HTTPException:
            await ctx.send("Couldn't position role correctly. Please check role hierarchy.")
        
        await self.config.guild(guild).team_role.set(role.id)
        await ctx.send(f"Team role created and configured: {role.mention}")

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add a user to the team list"""
        async with self.config.team_members() as members:
            if user.id not in members:
                members.append(user.id)
                await ctx.send(f"Added {user} to the team list.")
            else:
                await ctx.send(f"{user} is already in the team list.")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove a user from the team list"""
        async with self.config.team_members() as members:
            if user.id in members:
                members.remove(user.id)
                await ctx.send(f"Removed {user} from the team list.")
            else:
                await ctx.send(f"{user} is not in the team list.")

    @team.command()
    async def update(self, ctx):
        """Update team roles across all servers"""
        team_members = await self.config.team_members()
        for guild in self.bot.guilds:
            role_id = await self.config.guild(guild).team_role()
            if not role_id:
                await ctx.send(f"Server {guild.name} is not setup.")
                continue
            
            role = guild.get_role(role_id)
            if not role:
                await ctx.send(f"Role not found in {guild.name}.")
                continue
            
            # Check role position
            bot_top_role = guild.me.top_role
            if role.position >= bot_top_role.position:
                try:
                    await role.edit(position=bot_top_role.position - 1)
                except discord.HTTPException:
                    await ctx.send(f"Couldn't fix role position in {guild.name}.")
            
            # Sync members
            current_members = set(member.id for member in role.members)
            target_members = set(team_members)
            
            # Add missing members
            for user_id in target_members - current_members:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.add_roles(role)
                    except discord.HTTPException:
                        pass
            
            # Remove extra members
            for user_id in current_members - target_members:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.remove_roles(role)
                    except discord.HTTPException:
                        pass
            
        await ctx.send("Team roles updated across all servers.")

    @team.command()
    async def wipe(self, ctx):
        """Wipe all team data"""
        # Step 1: Password check
        await ctx.send("Type the password to confirm wipe:")
        pred = MessagePredicate.same_context(ctx)
        try:
            msg = await self.bot.wait_for("message", check=pred, timeout=30)
            if msg.content != "kkkkayaaaaa":
                return await ctx.send("Incorrect password.")
        except TimeoutError:
            return await ctx.send("Timed out.")
        
        # Step 2: Reaction confirmation
        confirm_msg = await ctx.send("Are you sure you want to wipe ALL data? (This cannot be undone!)")
        start_adding_reactions(confirm_msg, ReactionPredicate.YES_OR_NO_EMOJIS)
        
        pred = ReactionPredicate.yes_or_no(confirm_msg, ctx.author)
        try:
            await self.bot.wait_for("reaction_add", check=pred, timeout=30)
        except TimeoutError:
            return await ctx.send("Timed out.")
        
        if not pred.result:
            return await ctx.send("Cancelled.")
        
        # Wipe data
        await self.config.team_members.set([])
        
        # Delete roles in all guilds
        for guild in self.bot.guilds:
            role_id = await self.config.guild(guild).team_role()
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    try:
                        await role.delete()
                    except discord.HTTPException:
                        pass
            await self.config.guild(guild).team_role.set(None)
        
        await ctx.send("All team data and roles have been wiped.")

    @team.command()
    async def delete(self, ctx):
        """Delete the team role in this server"""
        guild = ctx.guild
        role_id = await self.config.guild(guild).team_role()
        if not role_id:
            return await ctx.send("No team role exists in this server.")
        
        role = guild.get_role(role_id)
        if role:
            try:
                await role.delete()
            except discord.HTTPException:
                await ctx.send("Failed to delete role.")
        await self.config.guild(guild).team_role.set(None)
        await ctx.send("Team role deleted in this server.")

async def setup(bot):
    await bot.add_cog(TeamCommands(bot))
