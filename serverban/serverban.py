import discord
from discord import app_commands
from redbot.core import commands
from redbot.core.bot import Red

# Set of allowed global user IDs for certain commands
ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
# Set of guild IDs where the user is blacklisted
server_blacklist = {1298444715804327967}

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option, appeal messaging, and blacklist control."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.blacklisted_users = {}  # {user_id: {"reason": ..., "added_by": ...}}

    # Command to add or remove users from the blacklist
    @app_commands.command(name="sbanbl", description="Add or remove users from the blacklist")
    @app_commands.describe(user_id="The ID of the user to blacklist", action="Whether to add or remove the user from the blacklist")
    async def sbanbl(self, interaction: discord.Interaction, user_id: str, action: str, reason: str = ""):
        """Add or remove users from the blacklist."""
        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to blacklist users.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        try:
            user_id = int(user_id)
        except ValueError:
            embed = discord.Embed(
                title="Invalid ID",
                description="Please provide a valid user ID as an integer.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        if action.lower() == "add":
            if reason == "":
                embed = discord.Embed(
                    title="Missing Reason",
                    description="You must provide a reason for adding a user to the blacklist.",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=embed, ephemeral=False)

            self.blacklisted_users[user_id] = {"reason": reason, "added_by": interaction.user.id}
            embed = discord.Embed(
                title="User Added to Blacklist",
                description=f"User with ID {user_id} has been added to the blacklist for reason: {reason}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

        elif action.lower() == "remove":
            if user_id in self.blacklisted_users:
                del self.blacklisted_users[user_id]
                embed = discord.Embed(
                    title="User Removed from Blacklist",
                    description=f"User with ID {user_id} has been removed from the blacklist.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="User Not Found",
                    description=f"User with ID {user_id} is not on the blacklist.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            embed = discord.Embed(
                title="Invalid Action",
                description="Invalid action. Use 'add' or 'remove'.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

    # Unban command (integrated with blacklist checking and global check)
    @app_commands.command(name="sunban", description="Unban a user and send them an invite link")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for unbanning the user")
    async def sunban(self, interaction: discord.Interaction, user_id: str, reason: str = "Your application has been accepted. You can now rejoin using the invite link."):
        """Unban a user and send them an invite link."""
        try:
            user_id = int(user_id)
        except ValueError:
            embed = discord.Embed(
                title="Invalid ID",
                description="Please provide a valid user ID as an integer.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        # Check if the server is blacklisted for global unbans
        if interaction.guild.id in server_blacklist:
            embed = discord.Embed(
                title="Server Blacklisted",
                description="This server has blacklisted global unbans. The user cannot be unbanned here.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        # If the user is blacklisted, show a confirmation before unbanning
        if user_id in self.blacklisted_users:
            blacklist_entry = self.blacklisted_users[user_id]
            embed = discord.Embed(
                title="Do Not Unban - User Blacklisted",
                description=f"This user is on the Do Not Unban list for reason: {blacklist_entry['reason']}\nAre you sure you want to proceed?",
                color=discord.Color.red()
            )
            view = discord.ui.View()
            yes_button = discord.ui.Button(label="Yes, Unban", style=discord.ButtonStyle.green)
            no_button = discord.ui.Button(label="No, Cancel", style=discord.ButtonStyle.red)
            view.add_item(yes_button)
            view.add_item(no_button)

            async def yes_button_callback(interaction: discord.Interaction):
                await self._unban_user(interaction, user_id, reason)

            async def no_button_callback(interaction: discord.Interaction):
                embed = discord.Embed(
                    title="Action Cancelled",
                    description="Unban action has been canceled.",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)

            yes_button.callback = yes_button_callback
            no_button.callback = no_button_callback

            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        else:
            await self._unban_user(interaction, user_id, reason)

    async def _unban_user(self, interaction: discord.Interaction, user_id: int, reason: str):
        """Helper function to unban the user and send them an invite link."""
        guild = interaction.guild
        invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)

        try:
            # Try to unban the user
            await guild.unban(discord.Object(id=user_id), reason=reason)

            # If no error occurred, proceed to send DM to the user
            try:
                user = await self.bot.fetch_user(user_id)
                channel = user.dm_channel or await user.create_dm()

                embed = discord.Embed(
                    title="You have been unbanned",
                    description=f"**Reason:** {reason}\n\n**Server:** {guild.name}\n\nClick the button below to rejoin the server.",
                    color=discord.Color.green()
                )
                view = discord.ui.View()
                button = discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link)
                view.add_item(button)

                await channel.send(embed=embed, view=view)
            except discord.NotFound:
                embed = discord.Embed(
                    title="User Not Found",
                    description="The user may have deleted their account.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="Permission Error",
                    description="Could not DM the user. Ensure they have DMs open.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=False)

            embed = discord.Embed(
                title="User Unbanned",
                description=f"User with ID {user_id} has been unbanned from {guild.name}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except discord.NotFound:
            embed = discord.Embed(
                title="User Not Banned",
                description="The user is not banned.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I do not have permission to unban this user.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"An error occurred while unbanning: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

    # Force ban (global and local ban with optional appeal messaging)
    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.describe(user_id="The ID of the user to ban", reason="Reason for banning the user")
    @app_commands.choices(
        is_global=[app_commands.Choice(name="Yes", value="yes"), app_commands.Choice(name="No", value="no")]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: str, reason: str = None):
        """Ban a user by ID with optional global effect and DM appeal info."""
        try:
            user_id = int(user_id)
        except ValueError:
            embed = discord.Embed(
                title="Invalid ID",
                description="Please provide a valid user ID as an integer.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=False)

        # Defer the response to let Discord know you're working on it
        await interaction.response.defer()

        # Convert is_global to boolean from string (Yes = True, No = False)
        is_global = True if is_global.lower() == 'yes' else False

        if is_global and interaction.user.id not in ALLOWED_GLOBAL_IDS:
            embed = discord.Embed(
                title="Permission Denied",
                description="You are not authorized to use global bans.",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=embed, ephemeral=False)

        target_guilds = self.bot.guilds if is_global else [interaction.guild]

        if not reason:
            reason = f"Action requested by {interaction.user.name} ({interaction.user.id})"

        ban_errors = []  # List to store errors if any occur during banning

        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                
                if not is_banned:
                    await guild.ban(discord.Object(id=user_id), reason=reason)
                    embed = discord.Embed(
                        title="User Banned",
                        description=f"User with ID {user_id} has been banned from {guild.name}.",
                        color=discord.Color.green()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)

                else:
                    embed = discord.Embed(
                        title="User Already Banned",
                        description=f"User with ID {user_id} is already banned in {guild.name}.",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed, ephemeral=False)

            except Exception as e:
                # Add to list of errors
                embed = discord.Embed(
                    title="Error",
                    description=f"An error occurred while banning the user from {guild.name}: {e}",
                    color=discord.Color.red()
                )
                ban_errors.append(embed)

        # If there are any errors, send them as a message
        if ban_errors:
            for error_embed in ban_errors:
                await interaction.followup.send(embed=error_embed, ephemeral=False)
