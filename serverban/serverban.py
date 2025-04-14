import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"
BLACKLIST = {}  # Store blacklisted users and reasons in a dictionary (could be saved to a file/database)

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option and appeal messaging."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree  # Ensure slash commands are in sync

    async def sync_slash_commands(self):
        """Sync all slash commands."""
        self.tree.clear_commands(guild=None)  # Clear old commands
        self.tree.add_command(self.sban)
        self.tree.add_command(self.sunban)
        self.tree.add_command(self.sbanbl)  # Add sbanbl command
        await self.tree.sync()

    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.describe(user_id="The ID of the user to ban", reason="Reason for banning the user")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: str, reason: str = None):
        """Ban a user by ID with optional global effect and DM appeal info."""
        try:
            user_id = int(user_id)  # Convert user_id to an integer
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user

        # Defer the response to let Discord know you're working on it
        await interaction.response.defer()

        # Convert is_global to boolean from string (Yes = True, No = False)
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

        ban_errors = []  # List to store errors if any occur during banning

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

        # Send a final response only once, containing all the errors and successes
        if ban_errors:
            await interaction.followup.send("\n".join(ban_errors))
        else:
            # Make sure we indicate the global status in the final message
            global_status = "globally" if is_global else "locally"
            await interaction.followup.send(f"User {user_id} banned {global_status} in all target servers.")


    @app_commands.command(name="sunban", description="Unban a user and send them an invite link, trying to use past DMs first.")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for unbanning the user")
    async def sunban(self, interaction: discord.Interaction, user_id: str, reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below"):
        """Unban a user and send them an invite link, trying to use past DMs first."""
        try:
            user_id = int(user_id)  # Convert user_id to an integer
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        # Check if the user is in the blacklist
        if user_id in BLACKLIST:
            blacklist_info = BLACKLIST[user_id]
            embed = discord.Embed(
                title="This user is in the Do Not Unban list",
                description=f"This user has been blacklisted.\n\n"
                            f"Reason: {blacklist_info['reason']}\n"
                            f"Listed by: {blacklist_info['listed_by']}\n\n"
                            "Are you sure you want to proceed with the unban?",
                color=discord.Color.red()
            )

            # Creating the "Proceed" and "Cancel" buttons
            view = discord.ui.View()
            proceed_button = discord.ui.Button(label="Proceed", style=discord.ButtonStyle.green)
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)

            # Button click callbacks
            async def on_proceed_button_click(interaction: discord.Interaction):
                # Proceed with the unban logic here
                await self._unban_user(interaction, user_id, reason)
                await interaction.response.send_message("User unbanned successfully.")

            async def on_cancel_button_click(interaction: discord.Interaction):
                # Handle cancel button press, just send a cancellation message
                await interaction.response.send_message("Unban process cancelled.")

            proceed_button.callback = on_proceed_button_click
            cancel_button.callback = on_cancel_button_click

            view.add_item(proceed_button)
            view.add_item(cancel_button)

            # Send the confirmation embed with the buttons
            await interaction.response.send_message(embed=embed, view=view)
            return

        # If not blacklisted, proceed with unbanning the user
        await self._unban_user(interaction, user_id, reason)

    async def _unban_user(self, interaction: discord.Interaction, user_id: int, reason: str):
        """Unban a user and send them a link to rejoin."""
        guild = interaction.guild
        invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)

        try:
            # Try to unban the user directly without iterating through the bans list
            await guild.unban(discord.Object(id=user_id), reason=reason)

            # If no error occurred, proceed to send DM to the user
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

    # The blacklist command (to add/remove users to/from the list)
    @app_commands.command(name="sbanbl", description="Add or remove a user from the blacklist")
    @app_commands.describe(user_id="The ID of the user to blacklist or remove from blacklist", action="Action to take: 'add' or 'remove'", reason="Reason for blacklisting")
    async def sbanbl(self, interaction: discord.Interaction, user_id: str, action: str, reason: str = None):
        """Add or remove a user from the blacklist."""
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        if action.lower() == "add":
            if reason is None:
                return await interaction.response.send_message("You must provide a reason when adding to the blacklist.")
            BLACKLIST[user_id] = {"reason": reason, "listed_by": interaction.user.name}
            await interaction.response.send_message(f"User {user_id} has been added to the blacklist with the reason: {reason}.")
        elif action.lower() == "remove":
            if user_id in BLACKLIST:
                del BLACKLIST[user_id]
                await interaction.response.send_message(f"User {user_id} has been removed from the blacklist.")
            else:
                await interaction.response.send_message(f"User {user_id} is not in the blacklist.")
        else:
            await interaction.response.send_message("Invalid action. Use 'add' or 'remove'.")
