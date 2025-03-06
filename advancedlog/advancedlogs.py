import discord
from discord.ext import commands
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils import mod
from typing import Optional

class AdvancedLogs(commands.Cog):
    """Advanced logging for message, role, user, voice, channel, server, and invite events."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_guild(log_channel=None)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Logs deleted messages."""
        if not message.guild:
            return
        log_channel = await self._get_log_channel(message.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Message Deleted",
            description=f"**Message ID:** {message.id}\n"
                        f"**Content:** {message.content}\n"
                        f"**User:** {message.author.mention} ({message.author.id})\n"
                        f"**Channel:** {message.channel.mention}\n"
                        f"**Timestamp:** {discord.utils.format_dt(message.created_at)}",
            color=discord.Color.red(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Logs edited messages."""
        if not before.guild or before.content == after.content:
            return
        log_channel = await self._get_log_channel(before.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Message Edited",
            description=f"**Message ID:** {before.id}\n"
                        f"**User:** {before.author.mention} ({before.author.id})\n"
                        f"**Channel:** {before.channel.mention}\n"
                        f"**Before:** {before.content}\n"
                        f"**After:** {after.content}\n"
                        f"**Timestamp:** {discord.utils.format_dt(after.edited_at or after.created_at)}",
            color=discord.Color.blue(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Logs when a user joins the server."""
        log_channel = await self._get_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Member Joined",
            description=f"**User:** {member.mention} ({member.id})\n"
                        f"**Timestamp:** {discord.utils.format_dt(member.joined_at)}",
            color=discord.Color.green(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Logs when a user leaves the server."""
        log_channel = await self._get_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Member Left",
            description=f"**User:** {member.mention} ({member.id})\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.orange(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Logs when a user is banned."""
        log_channel = await self._get_log_channel(guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Member Banned",
            description=f"**User:** {user.mention} ({user.id})\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.dark_red(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Logs when a user is unbanned."""
        log_channel = await self._get_log_channel(guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Member Unbanned",
            description=f"**User:** {user.mention} ({user.id})\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.green(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Logs when a channel is created."""
        log_channel = await self._get_log_channel(channel.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Channel Created",
            description=f"**Channel:** {channel.mention} ({channel.id})\n"
                        f"**Type:** {channel.type}\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.blue(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Logs when a channel is deleted."""
        log_channel = await self._get_log_channel(channel.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Channel Deleted",
            description=f"**Channel:** {channel.name} ({channel.id})\n"
                        f"**Type:** {channel.type}\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.red(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Logs when a role is created."""
        log_channel = await self._get_log_channel(role.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Role Created",
            description=f"**Role:** {role.name} ({role.id})\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.blue(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Logs when a role is deleted."""
        log_channel = await self._get_log_channel(role.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Role Deleted",
            description=f"**Role:** {role.name} ({role.id})\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.red(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Logs when a role is updated."""
        log_channel = await self._get_log_channel(before.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="Role Updated",
            description=f"**Role:** {after.name} ({after.id})\n"
                        f"**Changes:** {self._get_role_changes(before, after)}\n"
                        f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
            color=discord.Color.blue(),
        )
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Logs when a member's roles or nickname is updated."""
        log_channel = await self._get_log_channel(before.guild)
        if not log_channel:
            return

        if before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="Member Roles Updated",
                    description=f"**User:** {after.mention} ({after.id})\n"
                                f"**Added Roles:** {', '.join(r.mention for r in added_roles) if added_roles else 'None'}\n"
                                f"**Removed Roles:** {', '.join(r.mention for r in removed_roles) if removed_roles else 'None'}\n"
                                f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
                    color=discord.Color.blue(),
                )
                await log_channel.send(embed=embed)

        if before.nick != after.nick:
            embed = discord.Embed(
                title="Member Nickname Updated",
                description=f"**User:** {after.mention} ({after.id})\n"
                            f"**Old Nickname:** {before.nick}\n"
                            f"**New Nickname:** {after.nick}\n"
                            f"**Timestamp:** {discord.utils.format_dt(discord.utils.utcnow())}",
                color=discord.Color.blue(),
            )
            await log_channel.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def logs(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the logging channel for advanced logs."""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Logging channel set to {channel.mention}.")

    async def _get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get the logging channel for the guild."""
        channel_id = await self.config.guild(guild).log_channel()
        if not channel_id:
            return None
        return guild.get_channel(channel_id)

    def _get_role_changes(self, before: discord.Role, after: discord.Role) -> str:
        """Get a string describing the changes between two roles."""
        changes = []
        if before.name != after.name:
            changes.append(f"Name: {before.name} → {after.name}")
        if before.color != after.color:
            changes.append(f"Color: {before.color} → {after.color}")
        if before.permissions != after.permissions:
            changes.append("Permissions changed")
        return "\n".join(changes) if changes else "No changes"

def setup(bot: Red):
    bot.add_cog(AdvancedLogs(bot))
