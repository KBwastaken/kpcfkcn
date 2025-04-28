import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands as red_commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

BAN_GIF_URL = "https://media.discordapp.net/attachments/1304911814857068605/1361786454862201075/c00kie-get-banned.gif"
UNBAN_GIF_URL = "https://media.discordapp.net/attachments/1304911814857068605/1361789020593455456/unban-fivem.gif"

class ServerBan(red_commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.blacklisted_users = {}  # DO NOT UNBAN list
        self.global_banned_users = {}  # Real global bans
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

    @app_commands.command(name="sban", description="Ban a user by ID (globally or locally).")
    @app_commands.describe(user_id="User ID to ban", reason="Reason for banning", is_global="Ban globally?")
    @app_commands.choices(is_global=[app_commands.Choice(name="No", value="no"), app_commands.Choice(name="Yes", value="yes")])
    @app_commands.checks.has_permissions(ban_members=True)
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = None):
        await interaction.response.defer()
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.followup.send(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        moderator = interaction.user
        is_global_ban = is_global.value.lower() == "yes"

        if is_global_ban and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send(embed=self._error_embed("You are not allowed to perform global bans."), ephemeral=True)

        if not reason:
            reason = "None provided"

        if is_global_ban:
            self.global_banned_users[user_id] = {"reason": reason, "banned_by": str(moderator)}

        try:
            user = await self.bot.fetch_user(user_id)
        except Exception:
            user = discord.Object(id=user_id)  # fallback if fetching fails

        embed = discord.Embed(
            title="Global Ban" if is_global_ban else "Server Ban",
            description=(f"{user.mention if hasattr(user, 'mention') else user_id} has been {'globally banned' if is_global_ban else 'banned'} for {reason}\n\n"
                         f"Command Requested by: {moderator.mention}"),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=BAN_GIF_URL)

        await interaction.followup.send(embed=embed)

        guilds = self.bot.guilds if is_global_ban else [interaction.guild]
        for guild in guilds:
            if guild.id in self.server_blacklist:
                continue
            try:
                await guild.ban(discord.Object(id=user_id), reason=f"Banned by {moderator} | Reason: {reason}")
            except Exception as e:
                await interaction.followup.send(embed=self._error_embed(f"Error banning in {guild.name}: {e}"), ephemeral=True)

    @app_commands.command(name="sunban", description="Unban a user by ID (globally or locally).")
    @app_commands.describe(user_id="User ID to unban", reason="Reason for unbanning", is_global="Unban globally?")
    @app_commands.choices(is_global=[app_commands.Choice(name="No", value="no"), app_commands.Choice(name="Yes", value="yes")])
    @app_commands.checks.has_permissions(ban_members=True)
    async def sunban(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = None):
        await interaction.response.defer()
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.followup.send(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        moderator = interaction.user
        is_global_unban = is_global.value.lower() == "yes"

        if not reason:
            reason = "None provided"

        try:
            user = await self.bot.fetch_user(user_id)
        except Exception:
            user = discord.Object(id=user_id)  # fallback if fetching fails

        embed = discord.Embed(
            title="Global Unban" if is_global_unban else "Server Unban",
            description=(f"{user.mention if hasattr(user, 'mention') else user_id} has been {'globally unbanned' if is_global_unban else 'unbanned'} for {reason}\n\n"
                         f"Command Requested by: {moderator.mention}"),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=UNBAN_GIF_URL)

        await interaction.followup.send(embed=embed)

        guilds = self.bot.guilds if is_global_unban else [interaction.guild]
        for guild in guilds:
            if guild.id in self.server_blacklist:
                continue
            try:
                await guild.unban(discord.Object(id=user_id), reason=f"Unbanned by {moderator} | Reason: {reason}")
            except Exception as e:
                await interaction.followup.send(embed=self._error_embed(f"Error unbanning in {guild.name}: {e}"), ephemeral=True)

    @red_commands.command(name="syncbans")
    @red_commands.is_owner()
    async def syncbans(self, ctx: red_commands.Context):
        """Syncs only the global bans to this server."""
        synced = []
        failed = []

        for user_id, data in self.global_banned_users.items():
            try:
                bans = await ctx.guild.bans()
                if any(entry.user.id == user_id for entry in bans):
                    continue
                await ctx.guild.ban(discord.Object(id=user_id), reason=f"Global Sync | Reason: {data['reason']}")
                synced.append(user_id)
            except Exception as e:
                failed.append((user_id, str(e)))

        embed = discord.Embed(
            title="Syncbans Completed",
            description=(f"✅ Synced {len(synced)} users.\n"
                         f"❌ Failed {len(failed)} users."),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

        if failed:
            fail_embed = discord.Embed(
                title="Syncban Errors",
                description="\n".join(f"❌ {user_id}: {error}" for user_id, error in failed),
                color=discord.Color.red()
            )
            await ctx.send(embed=fail_embed)
