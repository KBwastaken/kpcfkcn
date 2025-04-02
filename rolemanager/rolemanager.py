from redbot.core import commands
import discord
from discord import app_commands
from redbot.core.bot import Red

class RoleManager(commands.Cog):
    """Role Management Cog for Redbot."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree

    async def cog_load(self):
        """Ensure syncing happens when the cog is loaded."""
        await self.sync_slash_commands()

    async def sync_slash_commands(self):
        """Sync the slash commands."""
        self.tree.clear_commands(guild=None)  # Clear old commands
        self.tree.add_command(self.assignrole)
        self.tree.add_command(self.unassignrole)
        self.tree.add_command(self.assignmultirole)
        self.tree.add_command(self.unassignmultirole)
        self.tree.add_command(self.massrole)
        self.tree.add_command(self.roleif)
        await self.tree.sync()

    def can_assign_role(self, user: discord.Member, role: discord.Role):
        """Check if the user can assign the given role based on hierarchy."""
        # If the user is the exempted user, return True
        if user.id == 1174820638997872721:
            return True
        
        # Check if the role to be assigned is higher than user's highest role
        highest_role = user.top_role
        if role.position > highest_role.position:
            return False
        return True

    # Prefix command for assignrole
    @commands.command(name="assignrole", description="Assigns a role to a user.")
    async def assignrole_prefix(self, ctx, role: discord.Role, user: discord.Member):
        """Assign a role to a user using prefix."""
        if not self.can_assign_role(ctx.author, role):
            return await ctx.send("You cannot assign a role higher than your current highest role.")
        
        await user.add_roles(role)
        await ctx.send(f"Assigned {role.name} to {user.display_name}.")

    # Slash command for assignrole
    @app_commands.command(name="assignrole", description="Assigns a role to a user.")
    @app_commands.describe(role="Role to assign", user="User to assign role to")
    async def assignrole_slash(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        """Assign a role to a user using slash."""
        if not self.can_assign_role(interaction.user, role):
            return await interaction.response.send_message("You cannot assign a role higher than your current highest role.", ephemeral=True)
        
        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned {role.name} to {user.display_name}.", ephemeral=False)

    # Prefix command for unassignrole
    @commands.command(name="unassignrole", description="Removes a role from a user.")
    async def unassignrole_prefix(self, ctx, role: discord.Role, user: discord.Member):
        """Remove a role from a user using prefix."""
        if not self.can_assign_role(ctx.author, role):
            return await ctx.send("You cannot remove a role higher than your current highest role.")
        
        await user.remove_roles(role)
        await ctx.send(f"Removed {role.name} from {user.display_name}.")

    # Slash command for unassignrole
    @app_commands.command(name="unassignrole", description="Removes a role from a user.")
    @app_commands.describe(role="Role to remove", user="User to remove role from")
    async def unassignrole_slash(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        """Remove a role from a user using slash."""
        if not self.can_assign_role(interaction.user, role):
            return await interaction.response.send_message("You cannot remove a role higher than your current highest role.", ephemeral=True)
        
        await user.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {user.display_name}.", ephemeral=False)

    # Prefix command for assignmultirole
    @commands.command(name="assignmultirole", description="Assign multiple roles to a user (max 6).")
    async def assignmultirole_prefix(self, ctx, user: discord.Member, *roles: discord.Role):
        """Assign multiple roles to a user (max 6) using prefix."""
        if len(roles) > 6:
            return await ctx.send("You can assign a maximum of 6 roles at a time.")
        if any(not self.can_assign_role(ctx.author, role) for role in roles):
            return await ctx.send("You cannot assign a role higher than your current highest role.")
        
        await user.add_roles(*roles)
        await ctx.send(f"Assigned {', '.join([role.name for role in roles])} to {user.display_name}.")

    # Slash command for assignmultirole
    @app_commands.command(name="assignmultirole", description="Assign multiple roles to a user (max 6).")
    @app_commands.describe(user="User to assign roles to", roles="Roles to assign")
    async def assignmultirole_slash(self, interaction: discord.Interaction, user: discord.Member, *roles: discord.Role):
        """Assign multiple roles to a user (max 6) using slash."""
        if len(roles) > 6:
            return await interaction.response.send_message("You can assign a maximum of 6 roles at a time.", ephemeral=True)
        if any(not self.can_assign_role(interaction.user, role) for role in roles):
            return await interaction.response.send_message("You cannot assign a role higher than your current highest role.", ephemeral=True)
        
        await user.add_roles(*roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in roles])} to {user.display_name}.", ephemeral=False)

    # Prefix command for unassignmultirole
    @commands.command(name="unassignmultirole", description="Removes multiple roles from a user (max 6).")
    async def unassignmultirole_prefix(self, ctx, user: discord.Member, *roles: discord.Role):
        """Remove multiple roles from a user (max 6) using prefix."""
        if len(roles) > 6:
            return await ctx.send("You can remove a maximum of 6 roles at a time.")
        if any(not self.can_assign_role(ctx.author, role) for role in roles):
            return await ctx.send("You cannot remove a role higher than your current highest role.")
        
        await user.remove_roles(*roles)
        await ctx.send(f"Removed {', '.join([role.name for role in roles])} from {user.display_name}.")

    # Slash command for unassignmultirole
    @app_commands.command(name="unassignmultirole", description="Removes multiple roles from a user (max 6).")
    @app_commands.describe(user="User to remove roles from", roles="Roles to remove")
    async def unassignmultirole_slash(self, interaction: discord.Interaction, user: discord.Member, *roles: discord.Role):
        """Remove multiple roles from a user (max 6) using slash."""
        if len(roles) > 6:
            return await interaction.response.send_message("You can remove a maximum of 6 roles at a time.", ephemeral=True)
        if any(not self.can_assign_role(interaction.user, role) for role in roles):
            return await interaction.response.send_message("You cannot remove a role higher than your current highest role.", ephemeral=True)
        
        await user.remove_roles(*roles)
        await interaction.response.send_message(f"Removed {', '.join([role.name for role in roles])} from {user.display_name}.", ephemeral=False)

    # Prefix command for massrole
    @commands.command(name="massrole", description="Give or remove a role from all members.")
    async def massrole_prefix(self, ctx, role: discord.Role, action: str):
        """Give or remove a role from all members using prefix."""
        if action.lower() not in ["give", "remove"]:
            return await ctx.send("Invalid action. Use 'give' or 'remove'.")
        
        guild = ctx.guild
        members = guild.members
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            await ctx.send(f"Gave {role.name} to all members.")
        else:
            for member in members:
                if role in member.roles:
                    await member.remove_roles(role)
            await ctx.send(f"Removed {role.name} from all members.")

    # Slash command for massrole
    @app_commands.command(name="massrole", description="Give or remove a role from all members.")
    @app_commands.describe(role="Role to give or remove", action="Action to perform (give/remove)")
    async def massrole_slash(self, interaction: discord.Interaction, role: discord.Role, action: str):
        """Give or remove a role from all members using slash."""
        if action.lower() not in ["give", "remove"]:
            return await interaction.response.send_message("Invalid action. Use 'give' or 'remove'.", ephemeral=True)
        
        guild = interaction.guild
        members = guild.members
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            await interaction.response.send_message(f"Gave {role.name} to all members.")
        else:
            for member in members:
                if role in member.roles:
                    await member.remove_roles(role)
            await interaction.response.send_message(f"Removed {role.name} from all members.")

    # Prefix command for roleif
    @commands.command(name="roleif", description="Gives roles if a user has a specific role.")
    async def roleif_prefix(self, ctx, base_role: discord.Role, *roles: discord.Role):
        """Assign roles if a user has a specific role using prefix."""
        roles = roles[:6]  # Limit to 6 roles
        for member in ctx.guild.members:
            if base_role in member.roles:
                await member.add_roles(*roles)
        await ctx.send(f"Assigned {', '.join([role.name for role in roles])} to members with {base_role.name}.")

    # Slash command for roleif
    @app_commands.command(name="roleif", description="Gives roles if a user has a specific role.")
    @app_commands.describe(base_role="Role to check for", roles="Roles to assign if user has the base role")
    async def roleif_slash(self, interaction: discord.Interaction, base_role: discord.Role, *roles: discord.Role):
        """Assign roles if a user has a specific role using slash."""
        roles = roles[:6]  # Limit to 6 roles
        for member in interaction.guild.members:
            if base_role in member.roles:
                await member.add_roles(*roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in roles])} to members with {base_role.name}.")
