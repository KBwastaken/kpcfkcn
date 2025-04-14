import discord
from discord import app_commands
from discord.ext import commands as ext_commands
from redbot.core import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option, appeal messaging, and blacklist control."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.blacklisted_users = {}  # {user_id: {"reason": ..., "added_by": ...}}
        self.server_blacklist = set()  # set of guild ids

    @commands.Cog.listener()
    async def on_ready(self):
        await self.tree.sync()

    def _error_embed(self, message: str):
        return discord.Embed(
            title="Error",
            description=message,
            color=discord.Color.red()
        )

    def _success_embed(self, message: str):
        return discord.Embed(
            title="Success",
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
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n**Servers:** {'All Participating Servers' if is_global else interaction.guild.name}\n\nYou may appeal using the link below. Appeals will be reviewed within 12 hours.\nTry rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        results = []
        for guild in self.bot.guilds if is_global else [interaction.guild]:
            if guild.id in self.server_blacklist:
                results.append(f"❌ `{guild.name}`: Server is blacklisted.")
                continue
            try:
                is_banned = any(entry.user.id == user_id async for entry in guild.bans())
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

        if user_id in self.blacklisted_users:
            # Blacklisted, need confirmation
            blacklisted_info = self.blacklisted_users[user_id]
            confirm_embed = discord.Embed(
                title="User is Blacklisted",
                description=f"This user is on the Do Not Unban list for reason: {blacklisted_info['reason']}. Are you sure you want to proceed with the unban?",
                color=discord.Color.orange()
            )
            view = discord.ui.View()
            confirm_button = discord.ui.Button(label="Yes, Proceed", style=discord.ButtonStyle.green)
            cancel_button = discord.ui.Button(label="No, Cancel", style=discord.ButtonStyle.red)
            view.add_item(confirm_button)
            view.add_item(cancel_button)

            async def on_confirm(interaction: discord.Interaction):
                await self._unban_user(user_id, interaction, reason)

            confirm_button.callback = on_confirm
            cancel_button.callback = lambda interaction: interaction.response.send_message(embed=self._error_embed("Unban canceled."), ephemeral=True)
            
            return await interaction.followup.send(embed=confirm_embed, view=view)

        if not is_global:
            guild = interaction.guild
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                user = await self.bot.fetch_user(user_id)
                embed = discord.Embed(title="You have been unbanned", description=f"**Server:** {guild.name}\n**Reason:** {reason}", color=discord.Color.green())
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link))
                await user.send(embed=embed, view=view)
                return await interaction.followup.send(embed=self._success_embed(f"User `{user_id}` unbanned and invited to {guild.name}."))
            except Exception as e:
                return await interaction.followup.send(embed=self._error_embed(f"Error: {e}"))

        else:
            allowed_guilds = [g for g in self.bot.guilds if g.id not in self.server_blacklist]
            success_guilds = []
            view = discord.ui.View()

            for guild in allowed_guilds:
                try:
                    await guild.unban(discord.Object(id=user_id), reason=reason)
                    invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                    view.add_item(discord.ui.Button(label=guild.name, url=invite.url, style=discord.ButtonStyle.link))
                    success_guilds.append(guild.name)
                except Exception:
                    continue

            try:
                user = await self.bot.fetch_user(user_id)
                embed = discord.Embed(title="You have been unbanned from multiple servers", description=f"**Reason:** {reason}\nClick the buttons below to rejoin:", color=discord.Color.green())
                await user.send(embed=embed, view=view)
            except Exception:
                pass

            embed = discord.Embed(title="Global Unban Complete", description=f"Unbanned from: {', '.join(success_guilds)}", color=discord.Color.green())
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="sbanbl", description="Add or remove a user from the Do Not Unban blacklist.")
    @app_commands.describe(user_id="User ID to modify", action="Add or remove", reason="Reason if adding")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove")
    ])
    async def sbanbl(self, interaction: discord.Interaction, user_id: str, action: app_commands.Choice[str], reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message(embed=self._error_embed("Invalid user ID."), ephemeral=True)

        if action.value == "add":
            if not reason:
                return await interaction.response.send_message(embed=self._error_embed("Reason required when adding."), ephemeral=True)
            self.blacklisted_users[user_id] = {"reason": reason, "added_by": f"{interaction.user} ({interaction.user.id})"}
            embed = discord.Embed(title="Blacklist Updated", description=f"User `{user_id}` added to Do Not Unban list.", color=discord.Color.red())
            embed.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed)
        else:
            if user_id in self.blacklisted_users:
                del self.blacklisted_users[user_id]
                await interaction.response.send_message(embed=self._success_embed(f"User `{user_id}` removed from Do Not Unban list."))
            else:
                await interaction.response.send_message(embed=self._error_embed("User not found in the blacklist."), ephemeral=True)
