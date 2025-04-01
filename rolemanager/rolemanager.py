# rolemanager/rolemanager.py
from redbot.core import commands
import discord
from discord import app_commands
from redbot.core.bot import Red

class RoleManager(commands.Cog):
    """Role Management Cog for Redbot."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree

    async def sync_slash_commands(self):
        self.tree.clear_commands(guild=None)  # Clear old commands
        self.tree.add_command(self.assignrole)
        self.tree.add_command(self.unassignrole)
        self.tree.add_command(self.assignmultirole)
        self.tree.add_command(self.unassignmultirole)
        self.tree.add_command(self.massrole)
        self.tree.add_command(self.roleif)
        await self.tree.sync()

    @app_commands.command(name="assignrole", description="Assigns a role to a user.")
    @app_commands.describe(role="Role to assign", user="User to assign role to")
    async def assignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        """Assign a role to a user."""
        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned {role.name} to {user.display_name}.", ephemeral=True)

    @app_commands.command(name="unassignrole", description="Removes a role from a user.")
    @app_commands.describe(role="Role to remove", user="User to remove role from")
    async def unassignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        """Remove a role from a user."""
        await user.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {user.display_name}.", ephemeral=True)

    @app_commands.command(name="assignmultirole", description="Assign multiple roles to a user (max 6).")
    @app_commands.describe(
        user="User to assign roles to",
        role1="First role to assign",
        role2="Second role to assign",
        role3="Third role to assign",
        role4="Fourth role to assign",
        role5="Fifth role to assign",
        role6="Sixth role to assign"
    )
    async def assignmultirole(self, interaction: discord.Interaction, user: discord.Member, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None):
        """Assign multiple roles to a user (max 6)."""
        roles = [role for role in [role1, role2, role3, role4, role5, role6] if role]
        if not roles:
            return await interaction.response.send_message("No valid roles provided.", ephemeral=True)
        await user.add_roles(*roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in roles])} to {user.display_name}.", ephemeral=True)

    @app_commands.command(name="unassignmultirole", description="Removes multiple roles from a user (max 6).")
    @app_commands.describe(
        user="User to remove roles from",
        role1="First role to remove",
        role2="Second role to remove",
        role3="Third role to remove",
        role4="Fourth role to remove",
        role5="Fifth role to remove",
        role6="Sixth role to remove"
    )
    async def unassignmultirole(self, interaction: discord.Interaction, user: discord.Member, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None):
        """Remove multiple roles from a user (max 6)."""
        roles = [role for role in [role1, role2, role3, role4, role5, role6] if role]
        if not roles:
            return await interaction.response.send_message("No valid roles provided.", ephemeral=True)
        await user.remove_roles(*roles)
        await interaction.response.send_message(f"Removed {', '.join([role.name for role in roles])} from {user.display_name}.", ephemeral=True)

    @app_commands.command(name="massrole", description="Give or remove a role from all members.")
    async def massrole(self, interaction: discord.Interaction, role: discord.Role, action: str):
        """Give or remove a role from all members."""
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

    @app_commands.command(name="roleif", description="Gives roles if a user has a specific role.")
    async def roleif(self, interaction: discord.Interaction, base_role: discord.Role, roles: str):
        """Assign roles if a user has a specific role."""
        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(interaction.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await interaction.response.send_message("No valid roles found.", ephemeral=True)
        for member in interaction.guild.members:
            if base_role in member.roles:
                await member.add_roles(*discord_roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in discord_roles])} to members with {base_role.name}.")
