import discord
from discord import app_commands
from discord.ext import commands
from redbot.core import commands as red_commands
from discord import Interaction
from redbot.core.bot import Red
from typing import Optional
import json
import os

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380, 1113852494154579999}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"
BAN_GIF = "https://media.discordapp.net/attachments/1304911814857068605/1361786454862201075/c00kie-get-banned.gif"
UNBAN_GIF = "https://media.discordapp.net/attachments/1304911814857068605/1361789020593455456/unban-fivem.gif"
BANLIST_FILE = "global_ban_list.json"

class ServerBan(red_commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.blacklisted_users = {}
        self.server_blacklist = {1368969894242291742, 1298444715804327967}
        self._load_global_bans()

    def _load_global_bans(self):
        if os.path.exists(BANLIST_FILE):
            with open(BANLIST_FILE, "r") as f:
                self.global_ban_list = set(json.load(f))
        else:
            self.global_ban_list = set()

    def _save_global_bans(self):
        with open(BANLIST_FILE, "w") as f:
            json.dump(list(self.global_ban_list), f)

    def _error_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="❌ Error", description=message, color=discord.Color.red())

    def _success_embed(self, message: str) -> discord.Embed:
        return discord.Embed(title="✅ Success", description=message, color=discord.Color.green())

    def _action_embed(self, user: discord.User, action: str, reason: str, moderator: discord.User, is_global: bool) -> discord.Embed:
        title = "Global Ban" if action == "ban" and is_global else ("Global Unban" if is_global else action.capitalize())
        description = f"{user.mention} has been {'globally ' if is_global else ''}{action}ned for: {reason}"
        embed = discord.Embed(title=title, description=description, color=discord.Color.red() if action == "ban" else discord.Color.green())
        embed.set_footer(text=f"Command requested by {moderator.name}")
        embed.set_thumbnail(url=BAN_GIF if action == "ban" else UNBAN_GIF)
        return embed

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

        return await interaction.response.send_message(embed=self._success_embed("User added to the Do Not Unban list."), ephemeral=False)

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
            return await interaction.response.send_message(embed=self._error_embed("You are not authorized to use global bans."), ephemeral=True)

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        await interaction.response.defer(ephemeral=True)

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
            await user.send(embed=ban_embed)
        except discord.HTTPException:
            pass

        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]
        results = []
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

        if is_global:
            self.global_ban_list.add(user_id)
            self._save_global_bans()

        await interaction.followup.send(embed=discord.Embed(title="Ban Results", description="\n".join(results), color=discord.Color.orange()))
        await interaction.channel.send(embed=self._action_embed(user, "ban", reason, moderator, is_global))

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
        moderator = interaction.user

        await interaction.response.defer(ephemeral=True)

        if user_id in self.blacklisted_users:
            info = self.blacklisted_users[user_id]
            embed = discord.Embed(
                title="🚫 User is in the Do Not Unban List",
                description=(f"**Reason:** {info['reason']}\n"
                             f"**Listed by:** {info['added_by']}\n\n"
                             "Are you sure you want to proceed with the unban?"),
                color=discord.Color.orange()
            )
            return await interaction.followup.send(embed=embed)

        guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist] if is_global else [interaction.guild]
        results = []

        for guild in guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                results.append(f"✅ {guild.name}")
            except Exception as e:
                results.append(f"❌ {guild.name}: {e}")

        try:
            user = await self.bot.fetch_user(user_id)
            dm_embed = discord.Embed(
                title="You have been unbanned",
                description=f"Reason: {reason}",
                color=discord.Color.green()
            )
            await user.send(embed=dm_embed)
        except discord.HTTPException:
            pass

        if is_global:
            self.global_ban_list.discard(user_id)
            self._save_global_bans()

        await interaction.followup.send(embed=discord.Embed(
            title="Unban Results",
            description="\n".join(results),
            color=discord.Color.orange()
        ))

        try:
            await interaction.channel.send(embed=self._action_embed(user, "unban", reason, moderator, is_global))
        except Exception:
            pass

    @app_commands.command(name="bansync", description="Sync all globally banned users to this server.")
    async def bansync(self, interaction: discord.Interaction):
        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message(
                embed=self._error_embed("You are not authorized to use this command."),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)
        results = []

        for user_id in self.global_ban_list:
            try:
                is_banned = False
                async for entry in interaction.guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if not is_banned:
                    await interaction.guild.ban(discord.Object(id=user_id), reason="Global ban sync")
                    results.append(f"✅ {user_id}")
                else:
                    results.append(f"⚠️ {user_id}: Already banned")
            except Exception as e:
                results.append(f"❌ {user_id}: {e}")

        embed = discord.Embed(
            title="Ban Sync Results",
            description="\n".join(results) or "No bans were performed.",
            color=discord.Color.orange()
        )

        try:
            await interaction.followup.send(embed=embed)
        except discord.NotFound:
            await interaction.channel.send(embed=embed)

    @app_commands.command(name="massglobalban", description="Globally ban up to 5 users at once.")
    @app_commands.describe(
        user1="User ID #1 to ban",
        user2="User ID #2 to ban (optional)",
        user3="User ID #3 to ban (optional)",
        user4="User ID #4 to ban (optional)",
        user5="User ID #5 to ban (optional)",
        reason="Reason for banning (required)"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def massglobalban(
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
                embed=self._error_embed("You are not authorized to use global bans."),
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
        for user_id in user_ids:
            try:
                user = await self.bot.fetch_user(user_id)
            except Exception:
                results.append(f"❌ {user_id}: User not found")
                continue

            if user_id in self.global_ban_list:
                results.append(f"⚠️ {user}: Already globally banned")
                continue

            try:
                ban_embed = discord.Embed(
                    title="You have been banned",
                    description=(
                        f"**Reason:** {reason}\n\n"
                        f"**Servers:** KCN Globalban\n\n"
                        "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                        "Try rejoining after 24 hours. If still banned, you can reapply in 30 days."
                    ),
                    color=discord.Color.red()
                )
                ban_embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
                await user.send(embed=ban_embed)
            except discord.HTTPException:
                pass

            ban_success = False
            for guild in self.bot.guilds:
                if guild.id in self.server_blacklist:
                    continue
                try:
                    is_banned = False
                    async for entry in guild.bans():
                        if entry.user.id == user_id:
                            is_banned = True
                            break
                    if not is_banned:
                        await guild.ban(discord.Object(id=user_id), reason=reason)
                        ban_success = True
                except Exception:
                    pass

            if ban_success:
                self.global_ban_list.add(user_id)
                results.append(f"✅ {user}")
                try:
                    await interaction.channel.send(embed=self._action_embed(user, "ban", reason, interaction.user, is_global=True))
                except Exception:
                    pass
            else:
                results.append(f"❌ {user}: Could not ban in any guild")

        self._save_global_bans()

        await interaction.followup.send(
            embed=discord.Embed(
                title="Mass Global Ban Results",
                description="\n".join(results),
                color=discord.Color.orange()
            ),
            ephemeral=True
        )

@app_commands.command(name="globalbanlist", description="Shows the list of globally banned users.")
@app_commands.describe(ephemeral="Send the response as ephemeral (only visible to you).")
async def globalbanlist(self, interaction: discord.Interaction, ephemeral: Optional[bool] = True):
    if interaction.user.id not in ALLOWED_GLOBAL_IDS:
        return await interaction.response.send_message(
            embed=self._error_embed("You are not authorized to use this command."),
            ephemeral=True
        )

    if not self.global_ban_list:
        return await interaction.response.send_message(
            embed=self._success_embed("The global ban list is currently empty."),
            ephemeral=True
        )

    entries = [f"<@{user_id}> `{user_id}`" for user_id in self.global_ban_list]

    class BanListView(discord.ui.View):
        def __init__(self, entries, per_page, user, ephemeral):
            super().__init__(timeout=300)
            self.entries = entries
            self.per_page = per_page
            self.user = user
            self.ephemeral = ephemeral
            self.current_page = 0
            self.total_pages = (len(entries) - 1) // per_page + 1

            self.prev_button = discord.ui.Button(label="⬅ Previous", style=discord.ButtonStyle.secondary)
            self.next_button = discord.ui.Button(label="Next ➡", style=discord.ButtonStyle.secondary)
            self.stop_button = discord.ui.Button(label="❌ Close", style=discord.ButtonStyle.danger)

            self.prev_button.callback = self.prev_page
            self.next_button.callback = self.next_page
            self.stop_button.callback = self.stop

            self.update_buttons()

            self.add_item(self.prev_button)
            self.add_item(self.next_button)
            self.add_item(self.stop_button)

        def update_buttons(self):
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page >= self.total_pages - 1

        def get_current_embed(self):
            start = self.current_page * self.per_page
            end = start + self.per_page
            page_entries = self.entries[start:end]
            embed = discord.Embed(
                title=f"Global Ban List (Page {self.current_page + 1} of {self.total_pages})",
                description="\n".join(page_entries),
                color=discord.Color.orange()
            )
            return embed

        async def prev_page(self, interaction: discord.Interaction):
            if interaction.user != self.user:
                return await interaction.response.send_message("You can’t use these buttons.", ephemeral=True)
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

        async def next_page(self, interaction: discord.Interaction):
            if interaction.user != self.user:
                return await interaction.response.send_message("You can’t use these buttons.", ephemeral=True)
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_current_embed(), view=self)

        async def stop(self, interaction: discord.Interaction):
            if interaction.user != self.user:
                return await interaction.response.send_message("You can’t use these buttons.", ephemeral=True)
            await interaction.message.delete()
            self.stop()  # This line should be removed to avoid recursion

    view = BanListView(entries=entries, per_page=20, user=interaction.user, ephemeral=ephemeral)
    await interaction.response.send_message(embed=view.get_current_embed(), view=view, ephemeral=ephemeral)