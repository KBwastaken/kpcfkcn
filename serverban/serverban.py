import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.bot import Red
import asyncio

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    """Force-ban/unban users with global options and blacklist checking."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.unban_blacklist = {}  # {user_id: {"reason": str, "added_by": str}}

    async def sync_slash_commands(self):
        self.tree.clear_commands(guild=None)
        self.tree.add_command(self.sban)
        self.tree.add_command(self.sunban)
        self.tree.add_command(self.sbanbl)
        await self.tree.sync()

    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: str, reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user
        await interaction.response.defer()
        is_global = is_global.lower() == 'yes'

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send("You are not authorized to use global bans.")

        target_guilds = self.bot.guilds if is_global else [interaction.guild]
        reason = reason or f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Servers:** {'Global Ban' if is_global else interaction.guild.name}\n\n"
                            "You may appeal using the link below. Appeals are reviewed within 12 hours. "
                            "Try rejoining after 24 hours. If still banned, reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await interaction.followup.send("Could not DM the user, proceeding with the ban.")

        results = []
        for guild in target_guilds:
            try:
                if any(entry.user.id == user_id async for entry in guild.bans()):
                    results.append(f"Already banned in {guild.name}.")
                else:
                    await guild.ban(discord.Object(id=user_id), reason=reason)
                    results.append(f"Banned in {guild.name}.")
            except Exception as e:
                results.append(f"Error banning in {guild.name}: {e}")

        await interaction.followup.send("\n".join(results))

    @app_commands.command(name="sunban", description="Unban a user by ID with optional global scope.")
    @app_commands.choices(
        if_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sunban(self, interaction: discord.Interaction, user_id: str, if_global: str, reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Invalid user ID.")

        reason = reason or "Your application has been accepted. You may rejoin using the invite link."
        is_global = if_global.lower() == 'yes'

        # Check blacklist if not global
        if not is_global and user_id in self.unban_blacklist:
            info = self.unban_blacklist[user_id]
            embed = discord.Embed(
                title="⚠ Do Not Unban List",
                description=f"This user is blacklisted from being unbanned.\n\n"
                            f"**Reason:** {info['reason']}\n"
                            f"**Listed By:** {info['added_by']}\n\n"
                            "Are you sure you want to proceed?",
                color=discord.Color.orange()
            )

            class Confirm(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=30)
                    self.value = None

                @discord.ui.button(label="Proceed", style=discord.ButtonStyle.green)
                async def confirm(self, interaction_, button):
                    self.value = True
                    self.stop()

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
                async def cancel(self, interaction_, button):
                    self.value = False
                    self.stop()

            view = Confirm()
            await interaction.response.send_message(embed=embed, view=view)
            await view.wait()

            if not view.value:
                return await interaction.followup.send("Unban cancelled.")

        await interaction.response.defer()
        target_guilds = self.bot.guilds if is_global else [interaction.guild]

        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            return await interaction.followup.send("User not found.")

        results = []
        for guild in target_guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                try:
                    channel = user.dm_channel or await user.create_dm()
                    embed = discord.Embed(
                        title="You have been unbanned",
                        description=f"**Reason:** {reason}\n**Server:** {guild.name}\n\nClick below to rejoin.",
                        color=discord.Color.green()
                    )
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link))
                    await channel.send(embed=embed, view=view)
                except discord.Forbidden:
                    results.append(f"Unbanned in {guild.name} (DM failed).")
                else:
                    results.append(f"Unbanned and DM sent in {guild.name}.")
            except discord.NotFound:
                results.append(f"User was not banned in {guild.name}.")
            except Exception as e:
                results.append(f"Error in {guild.name}: {e}")

        await interaction.followup.send("\n".join(results))

    @app_commands.command(name="sbanbl", description="Add or remove a user from the Do Not Unban List.")
    @app_commands.describe(user_id="The ID of the user", reason="Why they're blacklisted", action="Add or Remove")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove")
        ]
    )
    async def sbanbl(self, interaction: discord.Interaction, user_id: str, action: str, reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Invalid user ID.")

        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message("You are not authorized to modify the blacklist.")

        if action == "add":
            if not reason:
                return await interaction.response.send_message("You must provide a reason to add to blacklist.")
            self.unban_blacklist[user_id] = {
                "reason": reason,
                "added_by": f"{interaction.user} ({interaction.user.id})"
            }
            embed = discord.Embed(
                title="User Blacklisted",
                description=f"User `{user_id}` has been added to the Do Not Unban List.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Listed by {interaction.user}")
            return await interaction.response.send_message(embed=embed)

        elif action == "remove":
            if user_id in self.unban_blacklist:
                del self.unban_blacklist[user_id]
                return await interaction.response.send_message(f"User `{user_id}` removed from blacklist.")
            return await interaction.response.send_message("User is not in the blacklist.")
