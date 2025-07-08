import discord
from redbot.core import commands, app_commands
from redbot.core.bot import Red
from typing import Union

class CheckBan(commands.Cog):
    """Check if a user is banned in any server the bot is in."""

    def __init__(self, bot: Red):
        self.bot = bot

    async def has_team_role(self, interaction: discord.Interaction) -> bool:
        role_name = "KCN | Team"
        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        role = discord.utils.get(member.roles, name=role_name)
        return role is not None

    @app_commands.command(name="checkban", description="Check if a user is banned in any server the bot is in.")
    @app_commands.describe(user="The user to check (mention or ID)")
    async def checkban(
        self,
        interaction: discord.Interaction,
        user: Union[discord.User, discord.Member]
    ):
        if not await self.has_team_role(interaction):
            return await interaction.response.send_message("Authorised role not found", ephemeral=True)

        banned_servers = []

        for guild in self.bot.guilds:
            try:
                async for ban_entry in guild.bans():  # <-- FIXED THIS LINE
                    if ban_entry.user.id == user.id:
                        banned_servers.append((guild.name, ban_entry.reason))
            except discord.Forbidden:
                continue  # no perms to view bans

        if banned_servers:
            msg = f"**{user}** is banned in the following server(s):\n"
            for guild_name, reason in banned_servers:
                reason_text = reason if reason else "No reason provided"
                msg += f"- {guild_name}: {reason_text}\n"
        else:
            msg = f"**{user}** is not banned in any servers I can check."

        await interaction.response.send_message(msg)
