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
        # Retrieve current commands to check if they're already registered
        current_commands = await self.tree.get_commands()

        # List of new commands
        new_commands = [
            self.assignrole,
            self.unassignrole,
            self.assignmultirole,
            self.unassignmultirole,
            self.massrole,
            self.roleif
        ]
        
        # Register new commands if they're not already in the list of current commands
        for command in new_commands:
            if command.name not in [cmd.name for cmd in current_commands]:
                self.tree.add_command(command)

        # Sync commands with Discord
        await self.tree.sync()

    def can_manage_role(self, interaction: discord.Interaction, role: discord.Role) -> bool:
        user = interaction.user
        if user.id == 1174820638997872721:  # Exempt user ID
            return True
        return user.top_role.position > role.position

    @app_commands.command(name="assignrole", description="Assigns a role to a user.")
    async def assignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member, ephemeral: bool = True):
        if not self.can_manage_role(interaction, role):
            return await interaction.response.send_message("You can't assign roles above your own.", ephemeral=True)
        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned {role.name} to {user.display_name}.", ephemeral=ephemeral)

    @app_commands.command(name="unassignrole", description="Removes a role from a user.")
    async def unassignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member, ephemeral: bool = True):
        if not self.can_manage_role(interaction, role):
            return await interaction.response.send_message("You can't remove roles above your own.", ephemeral=True)
        await user.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {user.display_name}.", ephemeral=ephemeral)

    @app_commands.command(name="assignmultirole", description="Assign multiple roles to a user (max 6).")
    async def assignmultirole(self, interaction: discord.Interaction, user: discord.Member, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None, ephemeral: bool = True):
        roles = [r for r in [role1, role2, role3, role4, role5, role6] if r]
        if not roles:
            return await interaction.response.send_message("No valid roles provided.", ephemeral=True)
        if any(not self.can_manage_role(interaction, role) for role in roles):
            return await interaction.response.send_message("You can't assign roles above your own.", ephemeral=True)
        await user.add_roles(*roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in roles])} to {user.display_name}.", ephemeral=ephemeral)

    @app_commands.command(name="unassignmultirole", description="Removes multiple roles from a user (max 6).")
    async def unassignmultirole(self, interaction: discord.Interaction, user: discord.Member, role1: discord.Role = None, role2: discord.Role = None, role3: discord.Role = None, role4: discord.Role = None, role5: discord.Role = None, role6: discord.Role = None, ephemeral: bool = True):
        roles = [r for r in [role1, role2, role3, role4, role5, role6] if r]
        if not roles:
            return await interaction.response.send_message("No valid roles provided.", ephemeral=True)
        if any(not self.can_manage_role(interaction, role) for role in roles):
            return await interaction.response.send_message("You can't remove roles above your own.", ephemeral=True)
        await user.remove_roles(*roles)
        await interaction.response.send_message(f"Removed {', '.join([role.name for role in roles])} from {user.display_name}.", ephemeral=ephemeral)

    @app_commands.command(name="massrole", description="Give or remove a role from all members.")
    async def massrole(self, interaction: discord.Interaction, role: discord.Role, action: str, ephemeral: bool = True):
        if not self.can_manage_role(interaction, role):
            return await interaction.response.send_message("You can't modify this role.", ephemeral=True)
        guild = interaction.guild
        members = guild.members
        if action.lower() == "give":
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            await interaction.response.send_message(f"Gave {role.name} to all members.", ephemeral=ephemeral)
        else:
            for member in members:
                if role in member.roles:
                    await member.remove_roles(role)
            await interaction.response.send_message(f"Removed {role.name} from all members.", ephemeral=ephemeral)

    @app_commands.command(name="roleif", description="Gives roles if a user has a specific role.")
    async def roleif(self, interaction: discord.Interaction, base_role: discord.Role, roles: str, ephemeral: bool = True):
        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(interaction.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await interaction.response.send_message("No valid roles found.", ephemeral=True)
        for member in interaction.guild.members:
            if base_role in member.roles:
                await member.add_roles(*discord_roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in discord_roles])} to members with {base_role.name}._
