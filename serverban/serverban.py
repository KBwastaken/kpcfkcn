import discord
from discord import app_commands
from discord.ext import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        # User blacklist for Do Not Unban list
        self.blacklisted_users = {}  # {user_id: {"reason": ..., "added_by": ...}}
        # Hardcoded server blacklist (guild IDs)
        self.server_blacklist = {1256345356199788667}

    @commands.Cog.listener()
    async def on_ready(self):
        await self.tree.sync()

    def _error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(
            title="❌ Error",
            description=message,
            color=discord.Color.red()
        )

    def _success_embed(self, message: str) -> discord.Embed:
        return discord.Embed(
            title="✅ Success",
            description=message,
            color=discord.Color.green()
        )

    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.describe(user_id="The ID of the user to ban", reason="Reason for banning the user", is_global="Should this ban be global?")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        moderator = interaction.user
        is_global = is_global.value.lower() == "yes"

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message(embed=self._error_embed("You are not authorized to use global bans."), ephemeral=True)

        await interaction.response.defer()

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            ban_embed = discord.Embed(
                title="You have been banned",
                description=(f"**Reason:** {reason}\n\n**Servers:** "
                             f"{'All Participating Servers' if is_global else interaction.guild.name}\n\n"
                             "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                             "Try rejoining after 24 hours. If still banned, you can reapply in 30 days."),
                color=discord.Color.red()
            )
            ban_embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            ban_embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=ban_embed)
        except discord.HTTPException:
            pass

        results = []
        # Process each guild where unban should occur
        for guild in self.bot.guilds if is_global else [interaction.guild]:
            if guild.id in self.server_blacklist:
                results.append(f"❌ `{guild.name}`: Server is blacklisted.")
                continue
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if not is_banned:
                    await guild.ban(discord.Object(id=user_id), reason=reason)
                    results.append(f"✅ `{guild.name}`")
                else:
                    results.append(f"⚠️ `{guild.name}`: Already banned")
            except Exception as e:
                results.append(f"❌ `{guild.name}`: {e}")

        summary = discord.Embed(title="Ban Results", description="\n".join(results), color=discord.Color.orange())
        summary.set_footer(text=f"Requested by {moderator}")
        await interaction.followup.send(embed=summary)

    @app_commands.command(name="sunban", description="Unban a user by ID and send them invite links.")
    @app_commands.describe(user_id="The ID of the user to unban", is_global="Should this unban be global?", reason="Reason for unbanning the user")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sunban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = "Your application has been accepted. You may rejoin using the invite link."):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        is_global = is_global.value.lower() == "yes"
        moderator = interaction.user
        await interaction.response.defer()

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send(embed=self._error_embed("You are not authorized to perform global unbans."), ephemeral=True)

        # If user is in Do Not Unban list, request confirmation
        if user_id in self.blacklisted_users:
            info = self.blacklisted_users[user_id]
            confirm_embed = discord.Embed(
                title="🚫 User is in the Do Not Unban List",
                description=(f"**Reason:** {info['reason']}\n"
                             f"**Listed by:** {info['added_by']}\n\n"
                             "Are you sure you want to proceed with the unban?"),
                color=discord.Color.orange()
            )
            view = discord.ui.View()
            confirm_button = discord.ui.Button(label="✅ Yes, Proceed", style=discord.ButtonStyle.success)
            cancel_button = discord.ui.Button(label="❌ No, Cancel", style=discord.ButtonStyle.danger)
            view.add_item(confirm_button)
            view.add_item(cancel_button)

            async def on_confirm(btn_inter: discord.Interaction):
                if btn_inter.user.id != interaction.user.id:
                    return await btn_inter.response.send_message("You are not authorized to respond to this confirmation.", ephemeral=True)
                await self._force_unban(user_id, interaction, reason, is_global)
                await btn_inter.response.defer()

            async def on_cancel(btn_inter: discord.Interaction):
                if btn_inter.user.id != interaction.user.id:
                    return await btn_inter.response.send_message("You are not authorized to respond to this confirmation.", ephemeral=True)
                await btn_inter.response.send_message(embed=self._error_embed("Unban canceled."), ephemeral=True)

            confirm_button.callback = on_confirm
            cancel_button.callback = on_cancel

            return await interaction.followup.send(embed=confirm_embed, view=view)

        await self._force_unban(user_id, interaction, reason, is_global)

    async def _force_unban(self, user_id: int, interaction: discord.Interaction, reason: str, is_global: bool):
        successful_unbans = []
        failed_unbans = []
        # If global unban, process all guilds except hardcoded ones;
        # else, only unban from the current guild.
        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]

        for guild in guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                successful_unbans.append((guild.name, invite.url))
            except Exception as e:
                failed_unbans.append(f"{guild.name}: {e}")

        try:
            user = await self.bot.fetch_user(user_id)
            if successful_unbans:
                dm_embed = discord.Embed(
                    title="🔓 You have been unbanned",
                    description=f"**Reason:** {reason}\n\nRejoin using the invites below:",
                    color=discord.Color.green()
                )
                for name, url in successful_unbans:
                    dm_embed.add_field(name=name, value=f"[Rejoin]({url})", inline=False)
                await user.send(embed=dm_embed)
        except Exception:
            pass  # If DM fails, ignore

        result_embed = discord.Embed(title="Unban Results", color=discord.Color.green() if successful_unbans else discord.Color.red())
        if successful_unbans:
            result_embed.add_field(name="Successful Unbans", value="\n".join(f"{name}: Invite Sent" for name, _ in successful_unbans), inline=False)
        if failed_unbans:
            result_embed.add_field(name="Failed Unbans", value="\n".join(failed_unbans), inline=False)
        await interaction.followup.send(embed=result_embed)


# Setup function for Red
async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
