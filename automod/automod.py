import discord
import asyncio
from datetime import datetime, timedelta
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold, box

import logging
import json
import os
import re

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
            "immune_roles": [],  # Store immune roles
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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if not await self.config.guild(message.guild).automod_enabled():
            return

        # Get the list of immune roles (including the ones added via guildrole)
        immune_roles = await self.config.guild(message.guild).get_raw("immune_roles", default=[])

        # Add the "KCN | Protected" role as a default immune role
        immune_roles.append(discord.utils.get(message.guild.roles, name="KCN | Protected").id)

        # Check if the user has any immune roles
        user_roles = [role.id for role in message.author.roles]
        if any(role_id in immune_roles for role_id in user_roles):
            return  # Skip automod actions for users with immune roles

        # Word matching - avoids substrings like "night" for "nig"
        words = re.findall(r"\b\w+\b", message.content.lower())
        if any(word in self.blocked_words for word in words):
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            await self.add_warning(message.guild, message.author, "Blocked word usage", message.content)
            await self.send_alert(message.guild, message.author, message.content)

    async def add_warning(self, guild: discord.Guild, user: discord.Member, reason: str, original_message: str):
        now = datetime.utcnow()
        warnings = await self.config.member(user).warnings()

        warnings = [w for w in warnings if datetime.fromisoformat(w["timestamp"]) + timedelta(days=self.warning_expiry_days) > now]

        warning_entry = {"reason": reason, "timestamp": now.isoformat(), "content": original_message}
        warnings.append(warning_entry)
        await self.config.member(user).warnings.set(warnings)

        warn_count = len(warnings)
        await self.send_dm(guild, user, original_message, warn_count)

        if warn_count >= self.max_warnings:
            await self.send_mute_dm(user)
            await self.global_mute(user)
            await self.send_warning_embed(guild, user, warnings)

    async def send_dm(self, guild: discord.Guild, user: discord.Member, original_message: str, warn_count: int):
        try:
            blocked_word = next((bw for bw in self.blocked_words if bw in original_message.lower()), "a blocked word")

            embed = discord.Embed(
                title=f"⚠️ Warning #{warn_count}: Blocked Word Usage",
                color=discord.Color.orange() if warn_count < self.max_warnings else discord.Color.red()
            )
            embed.add_field(name="Blocked Word Detected", value=blocked_word, inline=False)
            embed.add_field(name="Message", value=box(original_message), inline=False)

            if warn_count < self.max_warnings:
                embed.set_footer(text=f"This is warning {warn_count}/{self.max_warnings}. Continued violations may lead to a mute.")
            else:
                embed.set_footer(text="You've hit the max warnings and are being muted.")

            await user.send(embed=embed)
        except discord.Forbidden:
            pass

    async def send_mute_dm(self, user: discord.Member):
        try:
            embed = discord.Embed(
                title="You Have Been Muted",
                description=("You have received 3 warnings for using blocked words. As a result, you have been muted Glo.\n\n"
                             "You will remain muted until a moderator reviews your case and contacts you."),
                color=discord.Color.dark_red()
            )
            embed.set_footer(text="Please wait patiently for a moderator to reach out to you.")
            await user.send(embed=embed)
        except discord.Forbidden:
            pass

    async def send_warning_embed(self, guild: discord.Guild, user: discord.Member, warnings: list):
        alert_channel_id = await self.config.guild(guild).alert_channel()
        mod_roles_ids = await self.config.guild(guild).mod_roles()
        if not alert_channel_id:
            return

        alert_channel = guild.get_channel(alert_channel_id)
        if not alert_channel:
            return

        embed = discord.Embed(
            title=f"Warning Threshold Reached: {user}",
            color=discord.Color.red()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        for i, w in enumerate(warnings, 1):
            embed.add_field(name=f"Warning {i}", value=f"Reason: {w['reason']} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>\nMessage: {w['content']}", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")

        allowed_mentions = discord.AllowedMentions(roles=True, users=True, everyone=False)
        role_ping_text = " ".join(f"<@&{r}>" for r in mod_roles_ids)
        content = f"{user.mention} {role_ping_text}"

        await alert_channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)

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

    @automod.command()
    async def toggle(self, ctx: commands.Context):
        """Toggle the automod on or off."""
        current = await self.config.guild(ctx.guild).automod_enabled()
        new_state = not current
        await self.config.guild(ctx.guild).automod_enabled.set(new_state)
        state_text = "enabled" if new_state else "disabled"
        await ctx.send(f"Automod has been {state_text}.")

    @commands.has_permissions(manage_guild=True)
    @commands.command()
    async def warnings(self, ctx: commands.Context, user: discord.Member):
        """Check a user's warnings."""
        warnings = await self.config.member(user).warnings()
        if not warnings:
            return await ctx.send("No warnings.")
        msg = "\n".join(f"{i+1}. {w['reason']} — <t:{int(datetime.fromisoformat(w['timestamp']).timestamp())}:R>" for i, w in enumerate(warnings))
        await ctx.send(box(msg))

    @commands.has_permissions(manage_guild=True)
    @commands.command()
    async def clearwarns(self, ctx: commands.Context, user: discord.Member):
        """Clear a user's warnings."""
        await self.config.member(user).warnings.set([])
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

    @commands.is_owner()
    @commands.guild_only()
    @automod.command()
    async def guildrole(self, ctx: commands.Context, role_id: int, action: bool):
        """Add or remove additional immune roles (only by bot owner)."""
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send(f"Role with ID {role_id} not found.")

        immune_role_name = "KCN | Protected"
        current_immune_roles = await self.config.guild(ctx.guild).get_raw("immune_roles", default=[])

        # Prevent removal of "KCN | Protected"
        if role.name == immune_role_name:
            return await ctx.send(f"The role '{immune_role_name}' cannot be removed.")

        if action:  # Add role
            if role.id in current_immune_roles:
                return await ctx.send(f"{role.name} is already an immune role.")
            
            # Ensure only 1 immune role besides "KCN | Protected"
            if len(current_immune_roles) >= 1:
                return await ctx.send("You can only have one immune role besides 'KCN | Protected'. Remove the current immune role before adding a new one.")
            
            current_immune_roles.append(role.id)
            await self.config.guild(ctx.guild).immune_roles.set(current_immune_roles)
            await ctx.send(f"{role.name} has been added as the immune role.")
        
        else:  # Remove role
            if role.id not in current_immune_roles:
                return await ctx.send(f"{role.name} is not currently an immune role.")
            
            current_immune_roles.remove(role.id)
            await self.config.guild(ctx.guild).immune_roles.set(current_immune_roles)
            await ctx.send(f"{role.name} has been removed as the immune role.")

    async def send_alert(self, guild: discord.Guild, user: discord.Member, original_message: str):
        alert_channel_id = await self.config.guild(guild).alert_channel()
        if alert_channel_id:
            alert_channel = guild.get_channel(alert_channel_id)
            if alert_channel:
                embed = discord.Embed(
                    title=f"Blocked Word Alert — {user}",
                    description="User has sent a message containing a blocked word.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Message Content", value=box(original_message), inline=False)
                embed.set_footer(text=f"User ID: {user.id}")
                await alert_channel.send(embed=embed)
