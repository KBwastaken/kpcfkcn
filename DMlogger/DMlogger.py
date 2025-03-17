import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from datetime import datetime
import re

class DMLogger(commands.Cog):
    """Logs DMs sent to the bot and forwards them to a designated server/channel."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        self.config.register_global(dm_guild=None, dm_channel=None)
        
        # Predefined list of trusted domains
        self.trusted_domains = [
            "youtube.com",   # All YouTube domains allowed
            "discord.com",   # Discord links allowed
            "github.com",    # GitHub links allowed
            "twitter.com",   # Twitter links allowed
            "facebook.com",  # Facebook links allowed
            "reddit.com",    # Reddit links allowed
            "twitch.tv",     # Twitch links allowed
        ]

        # Predefined list of known scam/malicious domains
        self.scam_domains = [
            "youtu.be",      # YouTube short URL
            "bit.ly",        # URL shortener often used for scams
            "t.co",          # Twitter's short URL
            "tinyurl.com",   # URL shortener often misused
            "shortlink.com", # Spammy URL shortener
            "is.gd",         # URL shortener associated with spam
            "goo.gl",        # Retired short URL, but could still be used for malicious purposes
            "freebitco.in",  # Known for spam and fraud
            "coinurl.com",   # URL shortener for crypto scams
        ]

    @commands.admin()
    @commands.command()
    async def dmset(self, ctx, guild_id: int, channel_id: int):
        """Set the server and channel where DMs should be logged."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("Invalid Guild ID or bot is not in the server.")
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return await ctx.send("Invalid Channel ID or bot lacks permission.")
        
        await self.config.dm_guild.set(guild_id)
        await self.config.dm_channel.set(channel_id)
        await ctx.send(f"DMs will now be logged in {guild.name} - {channel.mention}")

    async def send_dm_log(self, user: discord.User, message: discord.Message):
        """Handles forwarding the DM to the configured channel."""
        guild_id = await self.config.dm_guild()
        channel_id = await self.config.dm_channel()
        
        if not guild_id or not channel_id:
            return  # No setup found
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        mutual_guilds = [g.name for g in self.bot.guilds if g.get_member(user.id)]
        mutual_guilds_text = ", ".join(mutual_guilds) if mutual_guilds else "None"
        
        message_content = message.content or "*No text content*"
        if len(message_content) > 1024:
            message_content = message_content[:1020] + "... (truncated)"
        
        # Check for suspicious or untrusted links
        suspicious_links = []
        for link in re.findall(r"https?:\/\/(?:www\.)?[^\s]+", message_content):
            domain = link.split("/")[2]
            
            # Allow YouTube domain and block shortened YouTube (youtu.be) links
            if "youtube.com" in domain and "youtu.be" not in domain:
                continue  # It's a valid YouTube link
            elif domain in self.scam_domains:  # Block known scam domains
                suspicious_links.append(link)
            elif domain not in self.trusted_domains:  # Allow other trusted domains
                suspicious_links.append(link)

        if suspicious_links:
            await channel.send(f"🚨 **Sketchy Link Alert!** 🚨\nUser: {user} ({user.id})\nMessage: {message_content}")
        
        embed = discord.Embed(title="DM Received", color=discord.Color.blue(), timestamp=datetime.utcnow())
        embed.add_field(name="From", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Message", value=message_content, inline=False)
        embed.set_footer(text=f"Mutual Servers: {mutual_guilds_text}")
        
        await channel.send(embed=embed)
        
        # Send attachments separately
        if message.attachments:
            for att in message.attachments:
                await channel.send(f"📎 **Attachment:** {att.url}")
        
        # Send stickers separately
        if message.stickers:
            for sticker in message.stickers:
                await channel.send(f"🖼️ **Sticker:** {sticker.name}\n{sticker.url}")
        
        # Voice message detection (if applicable)
        for attachment in message.attachments:
            if attachment.filename.endswith(".ogg") or "voice-message" in attachment.filename:
                await channel.send(f"🎙️ **Voice Message:** {attachment.url}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detects incoming DMs to the bot."""
        if message.guild is None and not message.author.bot:
            await self.send_dm_log(message.author, message)
