import discord
import asyncio
import re
from datetime import datetime, timedelta
from discord.ext import commands
from redbot.core import commands, Config
from redbot.core.bot import Red
from typing import Optional, Dict, List

class GodLogger(commands.Cog):
    """The absolute final form of Discord logging - now with 50-minute AFK purge."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9999999999, force_registration=True)
        self.config.register_guild(
            log_channel=None,
            ping_role=None,
            afk_threshold=50,
            voice_activity={},
            message_archive={}
        )
        self.voice_timers = {}
        self.message_cache = {}
        self.ghost_ping_threshold = timedelta(seconds=10)
        self.zero_width_pattern = re.compile(r"[\u200B-\u200D\uFEFF]")

    # ==================== CORE LOGGING ENGINE ====================
    async def _send_log(self, guild: discord.Guild, embed: discord.Embed, critical: bool = False):
        channel_id = await self.config.guild(guild).log_channel()
        role_id = await self.config.guild(guild).ping_role()
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        content = ""
        if critical and role_id:
            role = guild.get_role(role_id)
            if role:
                content = f"{role.mention} "

        await channel.send(content=content, embed=embed)

    # ==================== MESSAGE OMNI-TRACKING ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Full message lifecycle tracking"""
        if message.guild and not message.author.bot:
            # Store message in volatile cache
            self.message_cache[message.id] = {
                "content": message.content,
                "author": message.author.id,
                "channel": message.channel.id,
                "created_at": message.created_at,
                "attachments": [a.url for a in message.attachments]
            }

            # Hidden text detection
            if self.zero_width_pattern.search(message.content):
                embed = discord.Embed(
                    title="👻 Hidden Text Detected",
                    description=f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n||{message.content}||",
                    color=discord.Color.dark_grey()
                )
                await self._send_log(message.guild, embed, critical=True)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Edit chain analysis with timing"""
        if before.guild and before.content != after.content:
            edit_delay = (after.edited_at - before.created_at).total_seconds()
            
            embed = discord.Embed(
                title="✏️ Message Edited",
                description=(
                    f"**Author:** {before.author.mention}\n"
                    f"**Channel:** {before.channel.mention}\n"
                    f"**Edit Speed:** {edit_delay:.1f}s\n"
                    f"**Before:** {before.content}\n"
                    f"**After:** {after.content}"
                ),
                color=discord.Color.orange()
            )
            await self._send_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Complete deletion tracking system"""
        if message.guild and message.id in self.message_cache:
            data = self.message_cache[message.id]
            deletion_speed = datetime.utcnow() - data['created_at']
            
            # Normal deletion logging
            embed = discord.Embed(
                title="🗑️ Message Deleted",
                description=(
                    f"**Author:** <@{data['author']}>\n"
                    f"**Channel:** <#{data['channel']}>\n"
                    f"**Content:** {data['content']}\n"
                    f"**Attachments:** {len(data['attachments'])}\n"
                    f"**Lifetime:** {deletion_speed.total_seconds():.1f}s"
                ),
                color=discord.Color.red()
            )
            await self._send_log(message.guild, embed)

            # Ghost ping detection
            if deletion_speed < self.ghost_ping_threshold and message.mentions:
                embed = discord.Embed(
                    title="👻 Ghost Ping Detected",
                    description=(
                        f"**Deleted by:** {await self._get_deleter(message)}\n"
                        f"**Targets:** {', '.join([m.mention for m in message.mentions])}\n"
                        f"**Content:** {data['content']}"
                    ),
                    color=discord.Color.dark_purple()
                )
                await self._send_log(message.guild, embed, critical=True)

            del self.message_cache[message.id]

    # ==================== VOICE NUCLEAR TRACKING ====================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Ultimate voice activity tracker"""
        guild = member.guild
        
        # AFK Listener Purge System (50 minutes)
        if after.mute or after.deaf:
            self.voice_timers[member.id] = asyncio.create_task(
                self._afk_purge_timer(member, guild)
            )
        elif before.mute or before.deaf:
            if member.id in self.voice_timers:
                self.voice_timers[member.id].cancel()
                del self.voice_timers[member.id]

        # Voice pattern analysis
        now = datetime.utcnow()
        voice_data = await self.config.guild(guild).voice_activity()
        user_data = voice_data.get(str(member.id), [])
        
        if before.channel != after.channel:
            user_data.append({
                "action": "join" if after.channel else "leave",
                "timestamp": now.timestamp(),
                "channel": after.channel.id if after.channel else before.channel.id
            })
            
            # Detect rapid channel switches
            if len(user_data) > 3:
                last_three = user_data[-3:]
                time_diff = last_three[-1]['timestamp'] - last_three[0]['timestamp']
                if time_diff < 300:  # 5 minutes
                    embed = discord.Embed(
                        title="🔀 Rapid Voice Activity",
                        description=f"**User:** {member.mention}\n**Changes:** 3+ in 5 minutes",
                        color=discord.Color.orange()
                    )
                    await self._send_log(guild, embed)

            await self.config.guild(guild).voice_activity.set({**voice_data, str(member.id): user_data})

    async def _afk_purge_timer(self, member: discord.Member, guild: discord.Guild):
        """50-minute AFK annihilation system"""
        try:
            await asyncio.sleep(3000)  # 50 minutes
            if member.voice and (member.voice.mute or member.voice.deaf):
                await member.move_to(None)
                embed = discord.Embed(
                    title="☠️ AFK User Purged",
                    description=(
                        f"**User:** {member.mention}\n"
                        f"**Status:** {'Muted' if member.voice.mute else 'Deafened'}\n"
                        f"**Duration:** 50+ minutes"
                    ),
                    color=discord.Color.dark_red()
                )
                await self._send_log(guild, embed, critical=True)
        except:
            pass

    # ==================== SERVER-WIDE SENTRY SYSTEM ====================
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """Full server setting tracking"""
        changes = []
        
        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.icon != after.icon:
            changes.append(f"**Icon:** [Old]({before.icon.url}) → [New]({after.icon.url})")
        if before.rules_channel != after.rules_channel:
            changes.append(f"**Rules Channel:** {before.rules_channel.mention} → {after.rules_channel.mention}")

        if changes:
            embed = discord.Embed(
                title="⚙️ Server Settings Updated",
                description="\n".join(changes),
                color=discord.Color.blue()
            )
            await self._send_log(after, embed)

    # ==================== COMMAND OVERRIDE ====================
    @commands.group()
    @commands.is_owner()
    async def logs(self, ctx):
        """Master control for logging system"""
        pass

    @logs.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Set the holy log channel"""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"📜 Logging nexus set to {channel.mention}")

    @logs.command()
    async def guardian(self, ctx, role: discord.Role):
        """Designate guardian role for alerts"""
        await self.config.guild(ctx.guild).ping_role.set(role.id)
        await ctx.send(f"🛡️ Guardian role set to {role.mention}")

    @logs.command()
    async def disable(self, ctx):
        """Deactivate the sentry system"""
        await self.config.guild(ctx.guild).log_channel.set(None)
        await ctx.send("🔴 Omnipotent logging system disabled")

async def setup(bot: Red):
    await bot.add_cog(GodLogger(bot))
