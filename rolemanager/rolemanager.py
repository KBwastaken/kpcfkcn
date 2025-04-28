from redbot.core import commands
import discord
from discord import app_commands
from redbot.core.bot import Red
import asyncio

class RoleManager(commands.Cog):
    """Role Management Cog for Redbot."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree

    async def sync_slash_commands(self):
        """Sync all slash commands globally."""
        self.tree.clear_commands()  # Clear old commands
        self.tree.add_command(self.assignrole)
        self.tree.add_command(self.unassignrole)
        self.tree.add_command(self.assignmultirole)
        self.tree.add_command(self.unassignmultirole)
        self.tree.add_command(self.massrole)
        self.tree.add_command(self.roleif)
        await self.tree.sync()  # Sync globally

    async def cog_load(self):
        """Ensure commands are synced when the cog is loaded."""
        await self.sync_slash_commands()

    def has_higher_role(self, interaction: discord.Interaction, role: discord.Role):
        """Check if the bot or user can assign a role above their highest role."""
        user_top_role = interaction.user.top_role
        bot_top_role = interaction.guild.me.top_role

        # Ensure the role to be assigned is not higher than the user's or bot's highest role
        if role.position >= user_top_role.position:
            return f"You cannot assign a role higher or equal to your top role ({user_top_role.name})."
        if role.position >= bot_top_role.position:
            return f"I cannot assign a role higher or equal to my top role ({bot_top_role.name})."
        return None

    @app_commands.command(name="assignrole", description="Assigns a role to a user.")
    @app_commands.describe(role="Role to assign", user="User to assign role to")
    async def assignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        """Assign a role to a user."""
        error = self.has_higher_role(interaction, role)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned {role.name} to {user.display_name}.", ephemeral=False)

    @app_commands.command(name="unassignrole", description="Removes a role from a user.")
    @app_commands.describe(role="Role to remove", user="User to remove role from")
    async def unassignrole(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member):
        """Remove a role from a user."""
        error = self.has_higher_role(interaction, role)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        await user.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {user.display_name}.", ephemeral=False)

    @app_commands.command(name="assignmultirole", description="Assign multiple roles to a user (max 6).")
    @app_commands.describe(
        user="User to assign roles to",
        roles="Comma-separated list of roles to assign (max 6)"
    )
    async def assignmultirole(self, interaction: discord.Interaction, user: discord.Member, roles: str):
        """Assign multiple roles to a user (max 6)."""
        role_names = [r.strip() for r in roles.split(",")]
        roles = [discord.utils.get(interaction.guild.roles, name=role_name) for role_name in role_names]
        roles = [role for role in roles if role]  # Filter out any None values

        if not roles:
            return await interaction.response.send_message("No valid roles provided.", ephemeral=True)

        # Check if any role is above the user's or bot's top role
        for role in roles:
            error = self.has_higher_role(interaction, role)
            if error:
                return await interaction.response.send_message(error, ephemeral=True)

        await user.add_roles(*roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in roles])} to {user.display_name}.", ephemeral=False)

    @app_commands.command(name="unassignmultirole", description="Removes multiple roles from a user (max 6).")
    @app_commands.describe(
        user="User to remove roles from",
        roles="Comma-separated list of roles to remove (max 6)"
    )
    async def unassignmultirole(self, interaction: discord.Interaction, user: discord.Member, roles: str):
        """Remove multiple roles from a user (max 6)."""
        role_names = [r.strip() for r in roles.split(",")]
        roles = [discord.utils.get(interaction.guild.roles, name=role_name) for role_name in role_names]
        roles = [role for role in roles if role]  # Filter out any None values

        if not roles:
            return await interaction.response.send_message("No valid roles provided.", ephemeral=True)

        # Check if any role is above the user's or bot's top role
        for role in roles:
            error = self.has_higher_role(interaction, role)
            if error:
                return await interaction.response.send_message(error, ephemeral=True)

        await user.remove_roles(*roles)
        await interaction.response.send_message(f"Removed {', '.join([role.name for role in roles])} from {user.display_name}.", ephemeral=False)

    @app_commands.command(name="massrole", description="Give or remove a role from all members.")
    @app_commands.describe(action="Choose whether to give or remove the role")
    @app_commands.choices(action=[
        app_commands.Choice(name="Give", value="give"),
        app_commands.Choice(name="Remove", value="remove"),
    ])
    async def massrole(self, interaction: discord.Interaction, role: discord.Role, action: str):
        """Give or remove a role from all members."""
        error = self.has_higher_role(interaction, role)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        if action.lower() not in ["give", "remove"]:
            return await interaction.response.send_message("Invalid action. Use 'give' or 'remove'.", ephemeral=True)

        guild = interaction.guild
        members = guild.members
        if action.lower() == "give":
            for i, member in enumerate(members):
                if role not in member.roles:
                    await member.add_roles(role)
                if i % 10 == 0:  # Add delay every 10 members
                    await asyncio.sleep(0.5)
            await interaction.response.send_message(f"Gave {role.name} to all members.", ephemeral=False)
        else:
            for i, member in enumerate(members):
                if role in member.roles:
                    await member.remove_roles(role)
                if i % 10 == 0:  # Add delay every 10 members
                    await asyncio.sleep(0.5)
            await interaction.response.send_message(f"Removed {role.name} from all members.", ephemeral=False)

    @app_commands.command(name="roleif", description="Gives roles if a user has a specific role.")
    async def roleif(self, interaction: discord.Interaction, base_role: discord.Role, roles: str):
        """Assign roles if a user has a specific role."""
        error = self.has_higher_role(interaction, base_role)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        role_list = [role.strip() for role in roles.split(",")][:6]
        discord_roles = [discord.utils.get(interaction.guild.roles, name=role) for role in role_list]
        discord_roles = [role for role in discord_roles if role]
        if not discord_roles:
            return await interaction.response.send_message("No valid roles found.", ephemeral=True)

        # Check if any role to assign is above the user's or bot's top role
        for role in discord_roles:
            error = self.has_higher_role(interaction, role)
            if error:
                return await interaction.response.send_message(error, ephemeral=True)

        for member in interaction.guild.members:
            if base_role in member.roles:
                await member.add_roles(*discord_roles)
        await interaction.response.send_message(f"Assigned {', '.join([role.name for role in discord_roles])} to members with {base_role.name}.", ephemeral=False)
