from redbot.core import commands
import discord
from redbot.core.bot import Red
import logging
import asyncio

logger = logging.getLogger("red.RoleManager")

EXEMPT_USER_IDS = {1174820638997872721, 1288170951267057839}  # Consider moving this to config if needed

class RoleManager(commands.Cog):
    """
    Role Management Cog for Redbot.
    Provides commands for assigning and removing roles from users.
    """

    def __init__(self, bot: Red):
        self.bot = bot

    def can_manage_role(self, ctx: commands.Context, role: discord.Role) -> bool:
        """
        Check if the user can manage the specified role.
        """
        user = ctx.author
        if user.id in EXEMPT_USER_IDS:
            return True
        if not user.guild_permissions.manage_roles:
            return False
        return user.top_role.position > role.position

    async def safe_add_roles(self, member: discord.Member, roles):
        try:
            await member.add_roles(*roles)
            return True
        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot add roles to {member}")
        except discord.HTTPException as e:
            logger.error(f"HTTPException: {e}")
        return False

    async def safe_remove_roles(self, member: discord.Member, roles):
        try:
            await member.remove_roles(*roles)
            return True
        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot remove roles from {member}")
        except discord.HTTPException as e:
            logger.error(f"HTTPException: {e}")
        return False

    @commands.command(name="assignrole", help="Assign a role to a user.")
    async def assignrole(self, ctx: commands.Context, role: discord.Role, user: discord.Member):
        """Assign a single role to a user."""
        if not self.can_manage_role(ctx, role):
            return await ctx.send("You can't assign roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        if await self.safe_add_roles(user, [role]):
            await ctx.send(f"Assigned {role.name} to {user.display_name}.")
        else:
            await ctx.send(f"Failed to assign {role.name} to {user.display_name}.")

    @commands.command(name="unassignrole", help="Remove a role from a user.")
    async def unassignrole(self, ctx: commands.Context, role: discord.Role, user: discord.Member):
        """Remove a single role from a user."""
        if not self.can_manage_role(ctx, role):
            return await ctx.send("You can't remove roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        if await self.safe_remove_roles(user, [role]):
            await ctx.send(f"Removed {role.name} from {user.display_name}.")
        else:
            await ctx.send(f"Failed to remove {role.name} from {user.display_name}.")

    @commands.command(name="assignmultirole", help="Assign up to 6 roles to a user.")
    async def assignmultirole(self, ctx: commands.Context, user: discord.Member, *roles: discord.Role):
        """Assign multiple roles to a user (max 6)."""
        roles = roles[:6]  # Limit to 6 roles
        if not roles:
            return await ctx.send("No valid roles provided.", ephemeral=True)
        if any(not self.can_manage_role(ctx, role) for role in roles):
            return await ctx.send("You can't assign some roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        if await self.safe_add_roles(user, roles):
            await ctx.send(f"Assigned {', '.join(role.name for role in roles)} to {user.display_name}.")
        else:
            await ctx.send(f"Failed to assign roles to {user.display_name}.")

    @commands.command(name="unassignmultirole", help="Remove up to 6 roles from a user.")
    async def unassignmultirole(self, ctx: commands.Context, user: discord.Member, *roles: discord.Role):
        """Remove multiple roles from a user (max 6)."""
        roles = roles[:6]
        if not roles:
            return await ctx.send("No valid roles provided.", ephemeral=True)
        if any(not self.can_manage_role(ctx, role) for role in roles):
            return await ctx.send("You can't remove some roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        if await self.safe_remove_roles(user, roles):
            await ctx.send(f"Removed {', '.join(role.name for role in roles)} from {user.display_name}.")
        else:
            await ctx.send(f"Failed to remove roles from {user.display_name}.")

    @commands.command(name="massrole", help="Give or remove a role from all members.")
    async def massrole(self, ctx: commands.Context, role: discord.Role, action: str):
        """Give or remove a role from all members in the guild."""
        if not self.can_manage_role(ctx, role):
            return await ctx.send("You can't modify this role or you lack 'Manage Roles' permission.", ephemeral=True)
        members = [m for m in ctx.guild.members if not m.bot]
        successes = 0
        failures = 0
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    if await self.safe_add_roles(member, [role]):
                        successes += 1
                    else:
                        failures += 1
                    await asyncio.sleep(0.2)  # Rate limit
            await ctx.send(f"Gave {role.name} to {successes} members. Failed for {failures} members.")
        elif action.lower() == "remove":
            for member in members:
                if role in member.roles:
                    if await self.safe_remove_roles(member, [role]):
                        successes += 1
                    else:
                        failures += 1
                    await asyncio.sleep(0.2)
            await ctx.send(f"Removed {role.name} from {successes} members. Failed for {failures} members.")
        else:
            await ctx.send("Invalid action. Use 'give' or 'remove'.")

    @commands.command(name="roleif", help="Assign roles to users with a specific base role. Usage: [base role] [role1,role2,...]")
    async def roleif(self, ctx: commands.Context, base_role: discord.Role, roles: str):
        """Assign roles to users with a specific base role."""
        role_names = [r.strip() for r in roles.split(",")][:6]
        discord_roles = [discord.utils.get(ctx.guild.roles, name=name) for name in role_names]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await ctx.send("No valid roles found.", ephemeral=True)
        successes = 0
        for member in ctx.guild.members:
            if base_role in member.roles and not member.bot:
                if await self.safe_add_roles(member, discord_roles):
                    successes += 1
                await asyncio.sleep(0.1)
        await ctx.send(f"Assigned {', '.join(role.name for role in discord_roles)} to {successes} members with {base_role.name}.")

def setup(bot: Red):
    bot.add_cog(RoleManager(bot))
