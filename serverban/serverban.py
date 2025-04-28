import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands as red_commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

BAN_GIF = "https://media.discordapp.net/attachments/1304911814857068605/1361786454862201075/c00kie-get-banned.gif"
UNBAN_GIF = "https://media.discordapp.net/attachments/1304911814857068605/1361789020593455456/unban-fivem.gif"

class RejoinButton(discord.ui.View):
    def __init__(self, invite_link: str):
        super().__init__()
        self.add_item(discord.ui.Button(label="Rejoin Server", url=invite_link))

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
        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
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
    async def sunban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        is_global = is_global.value.lower() == "yes"
        reason = reason if reason else "None provided"

        await interaction.response.defer()

        user_tag = f"<@{user_id}>"

        embed = discord.Embed(
            title="Global Unban" if is_global else "Server Unban",
            description=(f"{user_tag} has been {'Globally unbanned' if is_global else 'unbanned'} for {reason}\n\n"
                         f"Command Requested by: {interaction.user.mention}"),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=UNBAN_GIF)

        await interaction.followup.send(embed=embed)

        # DM the user
        try:
            user = await self.bot.fetch_user(user_id)
            invite_link = None
            if interaction.guild:
                invites = await interaction.guild.invites()
                if invites:
                    invite_link = invites[0].url
                else:
                    invite = await interaction.channel.create_invite(max_uses=1, unique=True)
                    invite_link = invite.url

            dm_embed = discord.Embed(
                title="You have been unbanned",
                description=(f"Reason: Your application has been accepted. You may rejoin using the invite link.\n"
                             f"You have been unbanned from {interaction.guild.name}"),
                color=discord.Color.green()
            )
            if invite_link:
                await user.send(embed=dm_embed, view=RejoinButton(invite_link))
            else:
                await user.send(embed=dm_embed)
        except discord.HTTPException:
            await interaction.followup.send(embed=self._error_embed("Failed to DM the user."), ephemeral=True)

        await self._force_unban(user_id, interaction, reason, is_global)

    async def _force_unban(self, user_id: int, interaction: discord.Interaction, reason: str, is_global: bool):
        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]
        lines = []
        for guild in guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                lines.append(f"✅ {guild.name}")
            except discord.Forbidden as e:
                lines.append(f"❌ {guild.name}: {e}")
            except discord.HTTPException as e:
                lines.append(f"❌ {guild.name}: {e}")

        result = discord.Embed(title="Unban Results", description="\n".join(lines), color=discord.Color.orange())
        result.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=result, ephemeral=True)

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
        reason = reason if reason else "None provided"

        await interaction.response.defer()

        user_tag = f"<@{user_id}>"

        embed = discord.Embed(
            title="Global Ban" if is_global else "Server Ban",
            description=(f"{user_tag} has been {'globally banned' if is_global else 'banned'} for {reason}\n\n"
                         f"Command Requested by: {moderator.mention}"),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=BAN_GIF)

        await interaction.followup.send(embed=embed)

        # DM the user
        try:
            user = await self.bot.fetch_user(user_id)
            ban_embed = discord.Embed(
                title="You have been banned",
                description=(f"Reason: Action requested by {moderator} ({moderator.id})\n\n"
                             f"Servers: {interaction.guild.name}\n\n"
                             "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                             "Try rejoining after 24 hours. If still banned, you can reapply in 30 days."),
                color=discord.Color.red()
            )
            ban_embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            ban_embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=ban_embed)
        except discord.HTTPException:
            await interaction.followup.send(embed=self._error_embed("Failed to DM the user."), ephemeral=True)

        await self._force_ban(user_id, interaction, reason, is_global)

    async def _force_ban(self, user_id: int, interaction: discord.Interaction, reason: str, is_global: bool):
        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]
        lines = []
        for guild in guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if not is_banned:
                    await guild.ban(discord.Object(id=user_id), reason=reason)
                    lines.append(f"✅ {guild.name}")
                else:
                    lines.append(f"⚠️ {guild.name}: Already banned")
            except Exception as e:
                lines.append(f"❌ {guild.name}: {e}")

        summary = discord.Embed(title="Ban Results", description="\n".join(lines), color=discord.Color.orange())
        summary.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=summary, ephemeral=True)
