import discord
import logging
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.embed import Embed
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from .utils import create_team_role

log = logging.getLogger("red.globalrole")

class GlobalRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(team_members=[])
        self.config.register_guild(team_role_id=None)

    async def is_bot_owner(self, ctx):
        """Check if the user is the bot owner."""
        return await self.bot.is_owner(ctx.author)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """When the bot joins a guild, create the 'KCN | Team' role."""
        try:
            role = await create_team_role(guild, self.bot)
            await self.config.guild(guild).team_role_id.set(role.id)
            log.info(f"Created 'KCN | Team' role in {guild.name} (ID: {guild.id})")
        except Exception as e:
            log.error(f"Failed to create role in {guild.name}: {e}")

    @commands.group()
    async def team(self, ctx):
        """Manage the global 'KCN | Team' role."""
        if not await self.is_bot_owner(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add a user to the global 'KCN | Team' role."""
        if not await self.is_bot_owner(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

        async with self.config.team_members() as team_members:
            if user.id not in team_members:
                team_members.append(user.id)
                await ctx.send(f"Added {user.name} to the global team.")
                log.info(f"Added {user.name} (ID: {user.id}) to the global team.")
            else:
                await ctx.send(f"{user.name} is already in the global team.")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove a user from the global 'KCN | Team' role."""
        if not await self.is_bot_owner(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

        async with self.config.team_members() as team_members:
            if user.id in team_members:
                team_members.remove(user.id)
                await ctx.send(f"Removed {user.name} from the global team.")
                log.info(f"Removed {user.name} (ID: {user.id}) from the global team.")
            else:
                await ctx.send(f"{user.name} is not in the global team.")

    @team.command()
    async def delete(self, ctx):
        """Delete the 'KCN | Team' role in this server."""
        if not await self.is_bot_owner(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

        # Step 1: Confirmation
        await ctx.send("Are you sure you want to delete the 'KCN | Team' role in this server? Type `yes` to confirm.")
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except TimeoutError:
            await ctx.send("Command timed out. Please try again.")
            return

        if not pred.result:
            await ctx.send("Cancelled.")
            return

        # Step 2: Delete the role
        role_id = await self.config.guild(ctx.guild).team_role_id()
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                await role.delete(reason="Deleted by bot owner.")
                await ctx.send("Deleted the 'KCN | Team' role in this server.")
                log.info(f"Deleted 'KCN | Team' role in {ctx.guild.name} (ID: {ctx.guild.id})")
            else:
                await ctx.send("The 'KCN | Team' role does not exist in this server.")
        else:
            await ctx.send("The 'KCN | Team' role does not exist in this server.")

    @team.command()
    async def wipe(self, ctx):
        """Wipe all team members and remove the role from all servers."""
        if not await self.is_bot_owner(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

        # Step 1: Confirmation
        await ctx.send("Are you sure you want to wipe all team members and remove the 'KCN | Team' role from all servers? Type `yes` to confirm.")
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except TimeoutError:
            await ctx.send("Command timed out. Please try again.")
            return

        if not pred.result:
            await ctx.send("Cancelled.")
            return

        # Step 2: Remove all team members
        await self.config.team_members.set([])
        await ctx.send("Removed all team members from the database.")
        log.info("Wiped all team members from the database.")

        # Step 3: Remove the role from all servers
        for guild in self.bot.guilds:
            try:
                role_id = await self.config.guild(guild).team_role_id()
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        await role.delete(reason="Wiped by bot owner.")
                        log.info(f"Deleted 'KCN | Team' role in {guild.name} (ID: {guild.id})")
            except Exception as e:
                log.error(f"Failed to delete role in {guild.name}: {e}")
        await ctx.send("Removed the 'KCN | Team' role from all servers.")

    @team.command()
    async def update(self, ctx):
        """Update the 'KCN | Team' role across all servers."""
        if not await self.is_bot_owner(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

        team_members = await self.config.team_members()
        for guild in self.bot.guilds:
            try:
                role_id = await self.config.guild(guild).team_role_id()
                if not role_id:
                    role = await create_team_role(guild, self.bot)
                    await self.config.guild(guild).team_role_id.set(role.id)
                    role_id = role.id
                role = guild.get_role(role_id)
                if not role:
                    role = await create_team_role(guild, self.bot)
                    await self.config.guild(guild).team_role_id.set(role.id)
                for member_id in team_members:
                    member = guild.get_member(member_id)
                    if member and role not in member.roles:
                        await member.add_roles(role)
                        log.info(f"Added 'KCN | Team' role to {member.name} in {guild.name}.")
            except Exception as e:
                log.error(f"Failed to update roles in {guild.name}: {e}")
        await ctx.send("Updated the 'KCN | Team' role across all servers.")
