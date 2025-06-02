import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands as red_commands
from discord import Interaction
from redbot.core.bot import Red
from typing import Optional

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380, 1113852494154579999}
KICK_GIF = "https://media.discordapp.net/attachments/1340519019760979988/1379238536254853200/go-leave-me-alone.gif?ex=683f837c&is=683e31fc&hm=6f6277b48bcfa6e229a995e047fb6cdeef1e9f7846d35c5862b81c1049bcf683&="
SERVER_BLACKLIST = {1298444715804327967}

class ServerKick(red_commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree

    def _error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="❌ Error", description=message, color=discord.Color.red())

    def _success_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="✅ Success", description=message, color=discord.Color.green())

    def _action_embed(self, user: discord.User, action: str, reason: str, moderator: discord.User, is_global: bool) -> discord.Embed:
        title = "Global Kick" if action == "kick" and is_global else action.capitalize()
        description = f"{user.mention} has been {'globally ' if is_global else ''}{action}ed for: {reason}"
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Command requested by {moderator.name}")
        embed.set_thumbnail(url=KICK_GIF if action == "kick")
        return embed

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self.tree.sync()
        except Exception:
            pass

    @app_commands.command(name="skick", description="Kick a user by ID (globally or in this server).")
    @app_commands.describe(user_id="User ID to kick", reason="Reason for kicking", is_global="Kick in all servers?")
    @app_commands.choices(is_global=[app_commands.Choice(name="No", value="no"), app_commands.Choice(name="Yes", value="yes")])
    @app_commands.checks.has_permissions(kick_members=True)
    async def skick(self, interaction: discord.Interaction, user_id: str, is_global: app_commands.Choice[str], reason: str = None):
        try:
            user_id_int = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        is_global_flag = is_global.value.lower() == "yes"
        moderator = interaction.user

        if is_global_flag and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message(embed=self._error_embed("You are not authorized to use global kicks."), ephemeral=True)

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        await interaction.response.defer(ephemeral=True)

        try:
            user = await self.bot.fetch_user(user_id_int)
            dm_description = (f"You have been {'globally kicked' if is_global_flag else 'kicked'} from "
                              f"{'all servers in the network' if is_global_flag else interaction.guild.name}.\n\n"
                              f"**Reason:** {reason}")
            dm_embed = discord.Embed(
                title="You have been kicked",
                description=dm_description,
                color=discord.Color.orange()
            )
            await user.send(embed=dm_embed)
        except discord.HTTPException:
            pass

        guilds = [g for g in self.bot.guilds if g.id not in SERVER_BLACKLIST] if is_global_flag else [interaction.guild]
        results = []

        for guild in guilds:
            try:
                member = guild.get_member(user_id_int)
                if member is None:
                    results.append(f"⚠️ {guild.name}: User not found or not in guild")
                    continue
                await guild.kick(member, reason=reason)
                results.append(f"✅ {guild.name}")
            except Exception as e:
                results.append(f"❌ {guild.name}: {e}")

        await interaction.followup.send(embed=discord.Embed(title="Kick Results", description="\n".join(results), color=discord.Color.orange()))
        await interaction.channel.send(embed=self._action_embed(user, "kick", reason, moderator, is_global_flag))

    @app_commands.command(name="massglobalkick", description="Globally kick up to 5 users at once.")
    @app_commands.describe(
        user1="User ID #1 to kick",
        user2="User ID #2 to kick (optional)",
        user3="User ID #3 to kick (optional)",
        user4="User ID #4 to kick (optional)",
        user5="User ID #5 to kick (optional)",
        reason="Reason for kicking (required)"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def massglobalkick(
        self,
        interaction: Interaction,
        user1: str,
        reason: str,
        user2: Optional[str] = None,
        user3: Optional[str] = None,
        user4: Optional[str] = None,
        user5: Optional[str] = None,
    ):
        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message(
                embed=self._error_embed("You are not authorized to use global kicks."),
                ephemeral=True
            )

        user_ids_raw = [user1, user2, user3, user4, user5]
        user_ids = []

        for uid in user_ids_raw:
            if uid is None:
                continue
            try:
                user_ids.append(int(uid))
            except ValueError:
                return await interaction.response.send_message(
                    embed=self._error_embed(f"Invalid user ID: {uid}"),
                    ephemeral=True
                )

        await interaction.response.defer(ephemeral=True)

        results = []
        for user_id_int in user_ids:
            try:
                user = await self.bot.fetch_user(user_id_int)
            except Exception:
                results.append(f"❌ {user_id_int}: User not found")
                continue

            try:
                dm_description = (f"You have been globally kicked from all servers in the network.\n\n"
                                  f"**Reason:** {reason}")
                dm_embed = discord.Embed(
                    title="You have been kicked",
                    description=dm_description,
                    color=discord.Color.orange()
                )
                try:
                    await user.send(embed=dm_embed)
                except discord.HTTPException:
                    pass

                kick_success = False
                for guild in self.bot.guilds:
                    if guild.id in SERVER_BLACKLIST:
                        continue
                    member = guild.get_member(user_id_int)
                    if member is None:
                        continue
                    try:
                        await guild.kick(member, reason=reason)
                        kick_success = True
                    except Exception:
                        pass

                if kick_success:
                    results.append(f"✅ {user}")
                    try:
                        await interaction.channel.send(embed=self._action_embed(user, "kick", reason, interaction.user, is_global=True))
                    except Exception:
                        pass
                else:
                    results.append(f"❌ {user}: Could not kick in any guild")

            except Exception as e:
                results.append(f"❌ {user}: {e}")

        await interaction.followup.send(
            embed=discord.Embed(
                title="Mass Global Kick Results",
                description="\n".join(results),
                color=discord.Color.orange()
            ),
            ephemeral=True
        )
