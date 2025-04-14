import discord
from discord.ext import commands
from discord import app_commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"
blacklist = {}  # user_id: reason


class ServerBan(commands.Cog):  # ✅ Inheriting correctly now
    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree

    async def cog_load(self):
        # ✅ Proper lifecycle method to register slash commands
        self.tree.add_command(self.sban)
        self.tree.add_command(self.sunban)
        self.tree.add_command(self.sbanbl)
        await self.tree.sync()

    # --- SBAN COMMAND (unchanged) ---
    @app_commands.command(name="sban", description="Ban a user by ID with optional global effect and DM appeal info.")
    @app_commands.describe(user_id="The ID of the user to ban", reason="Reason for banning the user")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sban(self, interaction: discord.Interaction, user_id: str, is_global: str, reason: str = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user
        await interaction.response.defer()

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
        except Exception:
            pass  # DM failed, silently continue

        ban_errors = []
        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if is_banned:
                    ban_errors.append(f"Already banned in {guild.name}.")
                    continue

                await guild.ban(discord.Object(id=user_id), reason=reason)
                ban_errors.append(f"Banned {user_id} in {guild.name}.")
            except Exception as e:
                ban_errors.append(f"Failed in {guild.name}: {e}")

        await interaction.followup.send("\n".join(ban_errors))


    # --- SBANBL SLASH COMMAND ---
    @app_commands.command(name="sbanbl", description="Blacklist a user from being unbanned. Run again to remove.")
    @app_commands.describe(user_id="The user ID to toggle from blacklist", reason="Reason for blacklisting (if adding)")
    async def sbanbl(self, interaction: discord.Interaction, user_id: int, reason: str = None):
        if interaction.user.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.response.send_message("You are not authorized to use this command.")

        if user_id in blacklist:
            del blacklist[user_id]
            return await interaction.response.send_message(f"User {user_id} removed from the blacklist.")

        if not reason:
            return await interaction.response.send_message("Please provide a reason to blacklist this user.")

        blacklist[user_id] = reason
        await interaction.response.send_message(f"User {user_id} has been blacklisted: {reason}")


    # --- SUNBAN COMMAND ---
    @app_commands.command(name="sunban", description="Unban a user and send them an invite link. Global optional.")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for unbanning the user"
    )
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sunban(self, interaction: discord.Interaction, user_id: str, is_global: str,
                     reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below"):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        moderator = interaction.user
        await interaction.response.defer()
        is_global = True if is_global.lower() == 'yes' else False

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            return await interaction.followup.send("You are not authorized to perform global unbans.")

        target_guilds = self.bot.guilds if is_global else [interaction.guild]

        # BLACKLIST PROMPT ONLY IF NOT GLOBAL
        if not is_global and user_id in blacklist:
            bl_reason = blacklist[user_id]

            class ConfirmView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)
                    self.result = None

                @discord.ui.button(label="Yes, Unban", style=discord.ButtonStyle.success)
                async def confirm(self, i: discord.Interaction, b: discord.ui.Button):
                    self.result = True
                    await i.response.send_message("Proceeding...", ephemeral=True)
                    self.stop()

                @discord.ui.button(label="No, Cancel", style=discord.ButtonStyle.danger)
                async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
                    self.result = False
                    await i.response.send_message("Unban cancelled.", ephemeral=True)
                    self.stop()

            view = ConfirmView()
            embed = discord.Embed(
                title="⚠️ This user is blacklisted from unbans",
                description=f"**Reason:** {bl_reason}\n\nDo you still want to proceed?",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, view=view)
            await view.wait()

            if not view.result:
                return  # Cancelled

        results = []
        for guild in target_guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                results.append(f"Unbanned from {guild.name}")
            except discord.NotFound:
                results.append(f"Not banned in {guild.name}")
            except discord.Forbidden:
                results.append(f"No perms in {guild.name}")
            except Exception as e:
                results.append(f"{guild.name}: {e}")

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been unbanned",
                description=f"**Reason:** {reason}\n\nClick the button(s) below to rejoin.",
                color=discord.Color.green()
            )
            view = discord.ui.View()
            for guild in target_guilds:
                try:
                    invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                    view.add_item(discord.ui.Button(label=f"Rejoin {guild.name}", url=invite.url, style=discord.ButtonStyle.link))
                except Exception:
                    continue
            await user.send(embed=embed, view=view)
        except Exception:
            results.append("❌ Could not DM the user.")

        await interaction.followup.send("\n".join(results))
