import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands as red_commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(red_commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.blacklisted_users = {}  # user_id: {reason, added_by}
        self.server_blacklist = {1298444715804327967}

    def _error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="❌ Error", description=message, color=discord.Color.red())

    def _success_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="✅ Success", description=message, color=discord.Color.green())

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self.tree.sync()
        except Exception:
            pass

    @app_commands.command(name="sbanbl", description="Add or remove a user from the Do Not Unban list.")
    @app_commands.describe(user_id="User ID to add/remove", reason="Reason for blacklisting (if adding)")
    async def sbanbl(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        if user_id not in self.blacklisted_users:
            return await interaction.response.send_message(embed=self._error_embed("You are not authorized to perform this action."), ephemeral=True)

        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        if user_id in self.blacklisted_users:
            del self.blacklisted_users[user_id]
            return await interaction.response.send_message(embed=self._success_embed("User removed from the Do Not Unban list."), ephemeral=True)

        if not reason:
            return await interaction.response.send_message(embed=self._error_embed("Reason required when adding a user."), ephemeral=True)

        self.blacklisted_users[user_id] = {
            "reason": reason,
            "added_by": str(interaction.user)
        }

        return await interaction.response.send_message(embed=self._success_embed("User added to the Do Not Unban list."), ephemeral=True)

    @app_commands.command(name="sunban", description="Unban a user by ID.")
    @app_commands.describe(user_id="User ID to unban", is_global="Unban in all servers?", reason="Reason for unbanning")
    @app_commands.choices(is_global=[app_commands.Choice(name="No", value="no"), app_commands.Choice(name="Yes", value="yes")])
    @app_commands.checks.has_permissions(ban_members=True)
    async def sunban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = "Your application has been accepted. You may rejoin using the invite link."):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        is_global = is_global.value.lower() == "yes"
        await interaction.response.defer()

        if user_id in self.blacklisted_users:
            info = self.blacklisted_users[user_id]
            embed = discord.Embed(
                title="🚫 User is in the Do Not Unban List",
                description=(f"**Reason:** {info['reason']}\n"
                             f"**Listed by:** {info['added_by']}\n\n"
                             "Are you sure you want to proceed with the unban?"),
                color=discord.Color.orange()
            )
            view = discord.ui.View()
            confirm = discord.ui.Button(label="✅ Yes, Proceed", style=discord.ButtonStyle.success)
            cancel = discord.ui.Button(label="❌ No, Cancel", style=discord.ButtonStyle.danger)

            async def on_confirm(i):
                if i.user != interaction.user:
                    return await i.response.send_message("Not your action to confirm.", ephemeral=True)
                await self._force_unban(user_id, interaction, reason, is_global)
                await i.response.defer()

            async def on_cancel(i):
                if i.user != interaction.user:
                    return await i.response.send_message("Not your action to cancel.", ephemeral=True)
                await i.response.send_message("Unban cancelled by {interactionUser.user.username}.", ephemeral=False)

            confirm.callback = on_confirm
            cancel.callback = on_cancel
            view.add_item(confirm)
            view.add_item(cancel)
            return await interaction.followup.send(embed=embed, view=view)

        await self._force_unban(user_id, interaction, reason, is_global)

    async def _force_unban(self, user_id: int, interaction: discord.Interaction, reason: str, is_global: bool):
        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]
        success, failed = [], []

        for guild in guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                success.append((guild.name, invite.url))
            except discord.Forbidden as e:
                failed.append(f"❌ {guild.name}: {e}")
            except discord.HTTPException as e:
                failed.append(f"❌ {guild.name}: {e}")

        lines = []  # Ensure 'lines' is initialized
        try:
            user = await self.bot.fetch_user(user_id)
            if success:
                embed = discord.Embed(
                    title="You have been unbanned",
                    description=(f"**Reason:** {reason}\n"
                                 f"{'You have been unbanned from ' + ', '.join([name for name, _ in success]) if not is_global else 'You have been globally unbanned.'}\n\n"
                                 "Click the buttons below to rejoin:" if reason else "Click the buttons below to rejoin:"),
                    color=discord.Color.green()
                )
                view = discord.ui.View()
                for name, url in success:
                    view.add_item(discord.ui.Button(label=f"Rejoin {name[:20]}", url=url))
                await user.send(embed=embed, view=view)
            else:
                lines.append("❌ Failed to send DM to the user, but proceeding with the unban(s).")
        except discord.HTTPException:
            lines.append("❌ Failed to send DM to the user, but proceeding with the unban(s).")

        # Build the result embed for the unban process
        for name, _ in success:
            lines.append(f"✅ {name}")
        for fail in failed:
            lines.append(fail)

        result = discord.Embed(title="Unban Results", description="\n".join(lines), color=discord.Color.orange())
        result.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=result)

    @app_commands.command(name="sban", description="Ban a user by ID (globally or in this server).")
    @app_commands.describe(user_id="User ID to ban", reason="Reason for banning", is_global="Ban in all servers?")
    @app_commands.choices(is_global=[app_commands.Choice(name="No", value="no"), app_commands.Choice(name="Yes", value="yes")])
    @app_commands.checks.has_permissions(ban_members=True)
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        is_global = is_global.value.lower() == "yes"
        moderator = interaction.user

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message(embed=self._error_embed("You are not authorized to use global bans."), ephemeral=False)

        await interaction.response.defer()

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        lines = []  # Ensure 'lines' is initialized here for logging ban results

        try:
            user = await self.bot.fetch_user(user_id)
            ban_embed = discord.Embed(
                title="You have been banned",
                description=(f"**Reason:** {reason}\n\n**Servers:** "
                             f"{'KCN Globalban' if is_global else interaction.guild.name}\n\n"
                             "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                             "Try rejoining after 24 hours. If still banned, you can reapply in 30 days."),
                color=discord.Color.red()
            )
            ban_embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            ban_embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=ban_embed)
        except discord.HTTPException:
            # If DM failed, log the failure and continue banning the user
            lines.append("❌ Failed to send DM to the user, but proceeding with the ban(s).")

        # Continue with the ban process as usual
        results = []
        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]

        for guild in guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if not is_banned:
                    await guild.ban(discord.Object(id=user_id), reason=reason)
                    results.append(f"✅ {guild.name}")
                else:
                    results.append(f"⚠️ {guild.name}: Already banned")
            except Exception as e:
                results.append(f"❌ {guild.name}: {e}")

        # Add results to lines
        for res in results:
            lines.append(res)

        summary = discord.Embed(title="Ban Results", description="\n".join(lines), color=discord.Color.orange())
        summary.set_footer(text=f"Requested by {moderator}")
        await interaction.followup.send(embed=summary)
