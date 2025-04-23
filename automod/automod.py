import discord
import asyncio
import os
from datetime import datetime, timedelta
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold, box
import logging

log = logging.getLogger("red.automod")

class AutoMod(commands.Cog):
    """Automod integration with Discord AutoMod system."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=7129137129, force_registration=True)

        default_guild = {
            "alert_channel": None,
            "mod_roles": [],
            "muted_role": None,
            "automod_enabled": False,
        }

        default_user = {
            "warnings": []
        }

        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)

        self.warning_expiry_days = 14
        self.max_warnings = 3
        self.muted_role_name = "KCN | Muted"

        # Load blocked words from the external file
        self.blocked_words = self.load_blocked_words()

def load_blocked_words(self):
    try:
        base_path = os.path.dirname(__file__)
        file_path = os.path.join(base_path, "blocked_words.txt")
        with open(file_path, "r", encoding="utf-8") as f:
            words = [line.strip().lower() for line in f if line.strip()]
        return set(words)
    except FileNotFoundError:
        log.error("automod/blocked_words.txt not found.")
        return set()
    # ------------------- Event Listener -------------------

    @commands.Cog.listener()
    async def on_auto_moderation_action(self, action: discord.AutoModAction):
        """Handle AutoMod actions."""
        user = action.user
        reason = action.rule_name or "AutoMod violation"

        await self.add_warning(user, reason)

        # AutoMod Violations
        if action.action_type == discord.AutoModActionType.block_message:
            await self.send_alert(action.guild, f"Blocked message from {user.mention} due to: {reason}")
            await self.add_warning(user, "Blocked message due to: " + reason)

    # ------------------- Warning System -------------------

    async def add_warning(self, user: discord.User, reason: str):
        now = datetime.utcnow()
        warnings = await self.config.user(user).warnings()

        warnings = [w for w in warnings if datetime.fromisoformat(w["timestamp"]) + timedelta(days=self.warning_expiry_days) > now]

        warning_entry = {"reason": reason, "timestamp": now.isoformat()}
        warnings.append(warning_entry)
        await self.config.user(user).warnings.set(warnings)

        try:
            await user.send(f"You have received a warning: {reason}")
        except discord.Forbidden:
            pass

        if len(warnings) >= self.max_warnings:
            await self.global_mute(user)
            await self.send_warning_embed(user, warnings)

    async def send_warning_embed(self, user: discord.User, warnings: list):
        for guild in self.bot.guilds:
            alert_channel_id = await self.config.guild(guild).alert_channel()
            mod_roles_ids = await self.config.guild(guild).mod_roles()
            if not alert_channel_id:
                continue

            alert_channel = guild.get_channel(alert_channel_id)
            if not alert_channel:
                continue

            mod_roles = [guild.get_role(rid) for rid in mod_roles_ids if guild.get_role(rid)]

            embed = discord.Embed(
                title=f"{user} reached 3 warnings",
                color=discord.Color.red()
            )
            embed.set_author(name=str(user), icon_url=user.display_avatar.url)
            for i, w in enumerate(warnings, 1):
                embed.add_field(name=f"Warning {i}", value=f"{w['reason']} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>", inline=False)
            embed.set_footer(text=f"User ID: {user.id}")

            content = f"{user.mention} {' '.join(r.mention for r in mod_roles)}"
            await alert_channel.send(content=content, embed=embed)

    # ------------------- Mute System -------------------

    async def global_mute(self, user: discord.User):
        for guild in self.bot.guilds:
            role_id = await self.config.guild(guild).muted_role()
            if not role_id:
                continue
            role = guild.get_role(role_id)
            if not role:
                continue
            member = guild.get_member(user.id)
            if member:
                try:
                    await member.add_roles(role, reason="Reached 3 warnings")
                except discord.Forbidden:
                    pass

    # ------------------- Setup Command -------------------

    @commands.is_owner()
    @commands.guild_only()
    @commands.group()
    async def automod(self, ctx: commands.Context):
        """Automod configuration commands."""
        pass

    @automod.command()
    async def setup(self, ctx: commands.Context):
        """Walks through the automod setup and enables Discord's automod."""

        await ctx.send("Enter the alert channel (mention it):")
        try:
            msg = await self.bot.wait_for("message", timeout=60, check=lambda m: m.author == ctx.author)
            channel = msg.channel_mentions[0]
        except (IndexError, asyncio.TimeoutError):
            return await ctx.send("Setup cancelled or invalid channel.")

        await self.config.guild(ctx.guild).alert_channel.set(channel.id)

        await ctx.send("Mention the mod role(s) to notify on 3 warnings (comma-separated if multiple):")
        try:
            msg = await self.bot.wait_for("message", timeout=60, check=lambda m: m.author == ctx.author)
            roles = msg.role_mentions
        except asyncio.TimeoutError:
            return await ctx.send("Setup cancelled.")

        await self.config.guild(ctx.guild).mod_roles.set([r.id for r in roles])

        muted_role = discord.utils.get(ctx.guild.roles, name=self.muted_role_name)
        if not muted_role:
            muted_role = await ctx.guild.create_role(name=self.muted_role_name, reason="Automod setup: Create muted role")

        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False)
            except discord.Forbidden:
                continue

        await self.config.guild(ctx.guild).muted_role.set(muted_role.id)
        await ctx.send("Setup complete!")

    @automod.command()
    async def resetconfig(self, ctx: commands.Context):
        """Reset all configuration."""
        await self.config.guild(ctx.guild).clear()
        await ctx.send("Configuration reset.")

    # ------------------- Utility Commands -------------------

    @commands.is_owner()
    @commands.command()
    async def smute(self, ctx: commands.Context, user: discord.User):
        """Globally mute a user."""
        await self.global_mute(user)
        await ctx.send(f"{user.mention} has been muted in all shared servers.")

    @commands.is_owner()
    @commands.command()
    async def warnings(self, ctx: commands.Context, user: discord.User):
        """Check a user's warnings."""
        warnings = await self.config.user(user).warnings()
        if not warnings:
            return await ctx.send("No warnings.")
        msg = "\n".join(f"{i+1}. {w['reason']} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>" for i, w in enumerate(warnings))
        await ctx.send(box(msg))

    @commands.is_owner()
    @commands.command()
    async def clearwarns(self, ctx: commands.Context, user: discord.User):
        """Clear a user's warnings."""
        await self.config.user(user).warnings.set([])
        await ctx.send(f"Cleared warnings for {user.mention}.")

    async def send_alert(self, guild: discord.Guild, message: str):
        """Send alert in the configured alerts channel."""
        alert_channel_id = await self.config.guild(guild).alert_channel()
        if alert_channel_id:
            alert_channel = guild.get_channel(alert_channel_id)
            if alert_channel:
                await alert_channel.send(message)
