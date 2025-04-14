import discord
from discord import app_commands
from redbot.core import commands
from discord import Interaction
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


@app_commands.command(name="sunban", description="Unban a user and send them an invite link.")
@app_commands.describe(user_id="The ID of the user to unban", reason="Reason for unbanning the user", is_global="Unban globally across all servers?")
@app_commands.choices(is_global=[
    app_commands.Choice(name="Yes", value="yes"),
    app_commands.Choice(name="No", value="no")
])
async def sunban(self, interaction: discord.Interaction, user_id: str, reason: str, is_global: str):
    try:
        user_id = int(user_id)
    except ValueError:
        return await interaction.response.send_message("Please provide a valid user ID as an integer.")

    is_global = True if is_global.lower() == 'yes' else False

    if is_global and interaction.user.id not in ALLOWED_GLOBAL_IDS:
        return await interaction.response.send_message("You are not authorized to perform global unbans.")

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

        view = discord.ui.View()
        proceed = discord.ui.Button(label="Proceed", style=discord.ButtonStyle.green)
        cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)

        async def on_proceed(inter):
            await inter.response.send_message("Proceeding with unban...")
            await self._unban_user(interaction, user_id, reason, is_global)

        async def on_cancel(inter):
            await inter.response.send_message("Unban cancelled.")

        proceed.callback = on_proceed
        cancel.callback = on_cancel

        view.add_item(proceed)
        view.add_item(cancel)

        return await interaction.response.send_message(embed=embed, view=view)

    # Not blacklisted — proceed immediately
    await interaction.response.send_message("Unbanning user...")
    await self._unban_user(interaction, user_id, reason, is_global)


async def _unban_user(self, interaction: discord.Interaction, user_id: int, reason: str, is_global: bool):
    success = []
    failed = []
    invite = await interaction.guild.text_channels[0].create_invite(max_uses=1, unique=True)

    guilds_to_unban = self.bot.guilds if is_global else [interaction.guild]

    for g in guilds_to_unban:
        try:
            await g.unban(discord.Object(id=user_id), reason=reason)
            success.append(g.name)
        except discord.NotFound:
            failed.append(f"{g.name}: Not banned")
        except discord.Forbidden:
            failed.append(f"{g.name}: Missing permissions")
        except Exception as e:
            failed.append(f"{g.name}: {str(e)}")

    # Attempt to DM the user
    try:
        user = await self.bot.fetch_user(user_id)
        channel = user.dm_channel or await user.create_dm()
        embed = discord.Embed(
            title="You have been unbanned",
            description=f"**Reason:** {reason}\n\nClick below to rejoin the server.",
            color=discord.Color.green()
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Rejoin Server", style=discord.ButtonStyle.link, url=invite.url))
        await channel.send(embed=embed, view=view)
    except:
        pass  # Fails silently if DM doesn't work

    # Send final report
    msg = f"✅ Unbanned from: {', '.join(success)}\n"
    if failed:
        msg += f"❌ Failed in: {', '.join(failed)}"
    await interaction.followup.send(msg)


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
