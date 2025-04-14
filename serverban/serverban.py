import discord
from discord import app_commands
from redbot.core import commands  # Make sure to import from Red's core
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"
blacklist = {}  # user_id: reason

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option and appeal messaging."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree  # Ensure slash commands are in sync

    async def sync_slash_commands(self):
        """Sync all slash commands, ensuring no duplicates."""
        # Clear old commands and re-sync
        await self.tree.sync()  # No need to clear commands manually; syncing takes care of it

    async def cog_load(self):
        # Sync commands on cog load
        await self.sync_slash_commands()

    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.describe(user_id="The ID of the user to ban", reason="Reason for banning the user")
    @app_commands.choices(
        is_global=[app_commands.Choice(name="Yes", value="yes"), app_commands.Choice(name="No", value="no")]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: str, reason: str = None):
        """Ban a user by ID with optional global effect and DM appeal info."""
        try:
            user_id = int(user_id)  # Convert user_id to an integer
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user
        await interaction.response.defer()

        is_global = True if is_global.lower() == 'yes' else False

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send("You are not authorized to use global bans.")

        target_guilds = self.bot.guilds if is_global else [interaction.guild]

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Servers:** {'globalban' if is_global and len(target_guilds) > 1 else interaction.guild.name}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await interaction.followup.send("Could not DM the user, but proceeding with the ban.")

        ban_errors = []
        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if is_banned:
                    ban_errors.append(f"User is already banned in {guild.name}.")
                    continue

                await guild.ban(discord.Object(id=user_id), reason=reason)
                ban_errors.append(f"Banned {user_id} in {guild.name}.")
            except Exception as e:
                ban_errors.append(f"Failed to ban in {guild.name}: {e}")

        if ban_errors:
            await interaction.followup.send("\n".join(ban_errors))
        else:
            global_status = "globally" if is_global else "locally"
            await interaction.followup.send(f"User {user_id} banned {global_status} in all target servers.")

    @app_commands.command(name="sunban", description="Unban a user and send them an invite link, trying to use past DMs first.")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for unbanning the user")
    async def sunban(self, interaction: discord.Interaction, user_id: str, reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below"):
        """Unban a user and send them an invite link, trying to use past DMs first."""
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        guild = interaction.guild
        invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)

        try:
            await guild.unban(discord.Object(id=user_id), reason=reason)

            try:
                user = await self.bot.fetch_user(user_id)
                channel = user.dm_channel or await user.create_dm()

                embed = discord.Embed(
                    title="You have been unbanned",
                    description=f"**Reason:** {reason}\n\n"
                                f"**Server:** {guild.name}\n\n"
                                "Click the button below to rejoin the server.",
                    color=discord.Color.green()
                )
                view = discord.ui.View()
                button = discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link)
                view.add_item(button)

                await channel.send(embed=embed, view=view)
            except discord.NotFound:
                await interaction.response.send_message("User not found. They may have deleted their account.")
            except discord.Forbidden:
                await interaction.response.send_message("Could not DM the user.")

            await interaction.response.send_message(f"User with ID {user_id} has been unbanned from {guild.name}.")
        except discord.NotFound:
            await interaction.response.send_message("The user is not banned.")
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to unban this user.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred while unbanning: {e}")

    @app_commands.command(name="sbanbl", description="Blacklist a user from being unbanned.")
    @app_commands.describe(user_id="The ID of the user to blacklist", reason="Reason for blacklisting the user")
    async def sbanbl(self, interaction: discord.Interaction, user_id: str, reason: str):
        """Blacklist a user from being unbanned."""
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        # Check if user is authorized to use this command
        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message("You are not authorized to blacklist users.")

        # Blacklist the user
        blacklist[user_id] = reason
        await interaction.response.send_message(f"User with ID {user_id} has been blacklisted for the reason: {reason}")

    @app_commands.command(name="unban", description="Unban a user after checking blacklist.")
    @app_commands.describe(user_id="The ID of the user to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        """Unban a user and check if they are on the blacklist."""
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        # Check if the user is blacklisted
        if user_id in blacklist:
            reason = blacklist[user_id]
            confirmation_view = discord.ui.View()
            confirm_button = discord.ui.Button(label="Yes", style=discord.ButtonStyle.green)
            deny_button = discord.ui.Button(label="No", style=discord.ButtonStyle.red)
            confirmation_view.add_item(confirm_button)
            confirmation_view.add_item(deny_button)

            # Send confirmation message
            await interaction.response.send_message(
                f"This user is on the Do Not Unban List for reason: {reason}. Are you sure you want to proceed?",
                view=confirmation_view
            )
            return
        else:
            # Proceed with unbanning
            await interaction.response.send_message(f"User with ID {user_id} is not blacklisted. Proceeding with unban.")
            await interaction.guild.unban(discord.Object(id=user_id))

# Ensure proper registration of the cog
async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
