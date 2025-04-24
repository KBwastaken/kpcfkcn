import discord
import asyncio
from datetime import datetime, timedelta
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold, box

import logging
import json
import os

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

        default_member = {
            "warnings": []
        }

        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

        self.warning_expiry_days = 14
        self.max_warnings = 3
        self.muted_role_name = "KCN | Muted"

        self.blocked_words = self.load_blocked_words()

    def load_blocked_words(self):
        path = os.path.join(os.path.dirname(__file__), "blocked_words.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                words = json.load(f)
                return [w.lower() for w in words if isinstance(w, str)]
        except FileNotFoundError:
            log.error("blocked_words.txt not found.")
            return []
        except json.JSONDecodeError as e:
            log.error(f"JSON error in blocked_words.txt: {e}")
            return []

    # ------------------- Event Listener -------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        lowered = message.content.lower()
        if any(word in lowered.split() for word in self.blocked_words):
            immune_role = discord.utils.get(message.guild.roles, name="KCN | Protected")
            if immune_role and immune_role in message.author.roles:
                return

            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await self.add_warning(message.guild, message.author, "Blocked word usage", message.content)
            await self.send_alert(message.guild, message.author, message.content)

    # ------------------- Warning System -------------------

    async def add_warning(self, guild: discord.Guild, user: discord.Member, reason: str, original_message: str):
        now = datetime.utcnow()
        warnings = await self.config.member(guild, user).warnings()

        warnings = [w for w in warnings if datetime.fromisoformat(w["timestamp"]) + timedelta(days=self.warning_expiry_days) > now]

        warning_entry = {"reason": reason, "timestamp": now.isoformat(), "content": original_message}
        warnings.append(warning_entry)
        await self.config.member(guild, user).warnings.set(warnings)

        try:
            embed = discord.Embed(
                title="⚠️ Warning: Blocked Word Usage",
                description=f"You used a blocked word: **{reason.split(': ')[-1]}**",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Message", value=original_message.content if original_message else "Unknown", inline=False)
            embed.set_footer(text="If you think this is a mistake, please reply to this DM to contact moderators.")
            await user.send(embed=embed)
        except discord.Forbidden:
            pass


        if len(warnings) >= self.max_warnings:
            await self.global_mute(user)
            await self.send_warning_embed(guild, user, warnings)

    async def send_warning_embed(self, guild: discord.Guild, user: discord.Member, warnings: list):
        alert_channel_id = await self.config.guild(guild).alert_channel()
        mod_roles_ids = await self.config.guild(guild).mod_roles()
        if not alert_channel_id:
            return

        alert_channel = guild.get_channel(alert_channel_id)
        if not alert_channel:
            return

        embed = discord.Embed(
            title=f"{user} reached {self.max_warnings} warnings",
            color=discord.Color.red()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        for i, w in enumerate(warnings, 1):
            embed.add_field(name=f"Warning {i}", value=f"{w['reason']} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")

        allowed_mentions = discord.AllowedMentions(roles=True, users=True, everyone=False)
        role_ping_text = " ".join(f"<@&{r}>" for r in mod_roles_ids)
        content = f"{user.mention} {role_ping_text}"

        await alert_channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)

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
        """Walks through the automod setup."""
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

    @commands.has_permissions(manage_guild=True)
    @commands.command()
    async def warnings(self, ctx: commands.Context, user: discord.Member):
        """Check a user's warnings."""
        warnings = await self.config.member(ctx.guild, user).warnings()
        if not warnings:
            return await ctx.send("No warnings.")
        msg = "\n".join(f"{i+1}. {w['reason']} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>" for i, w in enumerate(warnings))
        await ctx.send(box(msg))

    @commands.has_permissions(manage_guild=True)
    @commands.command()
    async def clearwarns(self, ctx: commands.Context, user: discord.Member):
        """Clear a user's warnings."""
        await self.config.member(ctx.guild, user).warnings.set([])
        await ctx.send(f"Cleared warnings for {user.mention}.")

    @commands.has_permissions(moderate_members=True)
    @commands.command()
    async def smute(self, ctx: commands.Context, user: discord.User):
        """Globally mute a user."""
        await self.global_mute(user)
        await ctx.send(f"{user.mention} has been muted in all shared servers.")

    @commands.has_permissions(moderate_members=True)
    @commands.command()
    async def sunmute(self, ctx: commands.Context, user: discord.User):
        """Globally unmute a user."""
        for guild in self.bot.guilds:
            role_id = await self.config.guild(guild).muted_role()
            if not role_id:
                continue
            role = guild.get_role(role_id)
            if not role:
                continue
            member = guild.get_member(user.id)
            if member and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Manual unmute")
                except discord.Forbidden:
                    continue
        await ctx.send(f"{user.mention} has been unmuted in all shared servers.")

    async def send_alert(self, guild: discord.Guild, user: discord.Member, original_message: str):
        """Send alert in the configured alerts channel."""
        alert_channel_id = await self.config.guild(guild).alert_channel()
        if alert_channel_id:
            alert_channel = guild.get_channel(alert_channel_id)
            if alert_channel:
                await alert_channel.send(f"{user.mention} used a blocked word.\n**Message:** {box(original_message)}")
