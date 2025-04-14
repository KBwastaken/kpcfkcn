import discord
from discord import app_commands
from discord.ext import commands as ext_commands
from redbot.core import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153, 1113451234477752380}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.tree = bot.tree
        self.blacklist = {}  # user_id: {"reason": str, "listed_by": int}
        self.server_unban_blacklist = set()  # guild_ids

    async def sync_slash_commands(self):
        self.tree.clear_commands(guild=None)
        self.tree.add_command(self.sban)
        self.tree.add_command(self.sunban)
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
                description=f"**Reason:** {reason}\n\n**Servers:** {'globalban' if is_global and len(target_guilds) > 1 else interaction.guild.name}\n\nYou may appeal using the link below. Appeals will be reviewed within 12 hours.\nTry rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await interaction.followup.send("Could not DM the user, but proceeding with the ban.")

        ban_errors = []
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

        if ban_errors:
            await interaction.followup.send("\n".join(ban_errors))
        else:
            status = "globally" if is_global else "locally"
            await interaction.followup.send(f"User {user_id} banned {status} in all target servers.")

    @app_commands.command(name="sunban", description="Unban a user, optionally globally, with confirmation for blacklisted users.")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for unbanning", is_global="Unban globally?")
    @app_commands.choices(
        is_global=[
            app_commands.Choice(name="Yes", value="yes"),
            app_commands.Choice(name="No", value="no")
        ]
    )
    async def sunban(self, interaction: discord.Interaction, user_id: str, reason: str = None, is_global: str = "no"):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Please provide a valid user ID as an integer.")

        await interaction.response.defer()
        is_global = True if is_global.lower() == 'yes' else False
        reason = reason or "Your application has been accepted. You may rejoin using the invite link."

        user = await self.bot.fetch_user(user_id)

        # Check blacklist
        if not is_global and user_id in self.blacklist:
            data = self.blacklist[user_id]
            embed = discord.Embed(
                title="⚠️ Do Not Unban List",
                description=f"This user is on the Do Not Unban List.\n**Reason**: {data['reason']}\n**Listed By**: <@{data['listed_by']}>",
                color=discord.Color.red()
            )
            view = discord.ui.View()

            async def proceed_callback(interact):
                await self._unban_user(interact, user_id, user, reason, [interaction.guild])

            async def cancel_callback(interact):
                await interact.response.send_message("Unban cancelled.", ephemeral=True)

            yes = discord.ui.Button(label="Proceed", style=discord.ButtonStyle.green)
            no = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
            yes.callback = proceed_callback
            no.callback = cancel_callback
            view.add_item(yes)
            view.add_item(no)

            return await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        guilds = self.bot.guilds if is_global else [interaction.guild]
        success_invites = []
        for guild in guilds:
            if guild.id in self.server_unban_blacklist:
                continue
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                success_invites.append((guild.name, invite.url))
            except Exception:
                continue

        try:
            embed = discord.Embed(
                title="You have been unbanned",
                description=f"**Reason:** {reason}\n\n**Server:** {'GLOBAL' if is_global else interaction.guild.name}\n\nClick the buttons below to rejoin the allowed servers.",
                color=discord.Color.green()
            )
            view = discord.ui.View()
            for name, url in success_invites:
                view.add_item(discord.ui.Button(label=name, url=url, style=discord.ButtonStyle.link))
            await user.send(embed=embed, view=view)
        except Exception:
            await interaction.followup.send("Could not DM the user.")

        await interaction.followup.send(f"User {user_id} has been unbanned from {len(success_invites)} server(s).")

    @commands.command(name="sbanbl")
    async def sbanbl(self, ctx: commands.Context, user_id: int, action: str, *, reason: str = None):
        if ctx.author.id not in ALLOWED_GLOBAL_IDS:
            return await ctx.send("You do not have permission to use this command.")

        if action.lower() == "add":
            if not reason:
                return await ctx.send("Please provide a reason for adding the user to the blacklist.")
            self.blacklist[user_id] = {"reason": reason, "listed_by": ctx.author.id}
            await ctx.send(f"User `{user_id}` added to the Do Not Unban list.")
        elif action.lower() == "remove":
            self.blacklist.pop(user_id, None)
            await ctx.send(f"User `{user_id}` removed from the Do Not Unban list.")
        else:
            await ctx.send("Invalid action. Use `add` or `remove`.")

    @commands.command(name="sbansbl")
    async def sbansbl(self, ctx: commands.Context, guild_id: int):
        if ctx.author.id not in ALLOWED_GLOBAL_IDS:
            return await ctx.send("You do not have permission to modify the server blacklist.")

        if guild_id in self.server_unban_blacklist:
            self.server_unban_blacklist.remove(guild_id)
            await ctx.send(f"Guild ID `{guild_id}` removed from the unban blacklist.")
        else:
            self.server_unban_blacklist.add(guild_id)
            await ctx.send(f"Guild ID `{guild_id}` added to the unban blacklist. Users won't be unbanned globally from it.")

    async def _unban_user(self, interaction, user_id, user, reason, guilds):
        success_invites = []
        for guild in guilds:
            try:
                await guild.unban(discord.Object(id=user_id), reason=reason)
                invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
                success_invites.append((guild.name, invite.url))
            except Exception:
                continue

        try:
            embed = discord.Embed(
                title="You have been unbanned",
                description=f"**Reason:** {reason}\n\n**Server:** {interaction.guild.name}\n\nClick below to rejoin.",
                color=discord.Color.green()
            )
            view = discord.ui.View()
            for name, url in success_invites:
                view.add_item(discord.ui.Button(label=name, url=url, style=discord.ButtonStyle.link))
            await user.send(embed=embed, view=view)
        except Exception:
            pass

        await interaction.followup.send(f"User {user_id} has been unbanned from {len(success_invites)} server(s).")
