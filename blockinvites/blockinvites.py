import discord
import asyncio
from redbot.core import commands, Config, checks

class BlockInvites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=987654321)
        self.config.register_guild(block_invites=False, invite_cooldown=10)
    
    @commands.command()
    @checks.is_owner()
    async def blockinvites(self, ctx, cooldown: int = 10):
        """Toggle blocking new invite links from being created and set a cooldown."""
        guild = ctx.guild
        is_blocking_invites = await self.config.guild(guild).block_invites()
        
        if is_blocking_invites:
            await self.config.guild(guild).block_invites.set(False)
            await ctx.send("🔓 Invite creation is now **unblocked**.")
        else:
            await self.config.guild(guild).block_invites.set(True)
            await self.config.guild(guild).invite_cooldown.set(cooldown)
            await ctx.send(f"🔒 Invite creation is now **blocked**. Cooldown set to {cooldown} seconds.")
            await self.delete_existing_invites(guild)
    
    async def delete_existing_invites(self, guild):
        """Delete all existing invites in the guild."""
        try:
            invites = await guild.invites()
            for invite in invites:
                await invite.delete(reason="Auto-deleting existing invites due to invite block.")
        except discord.HTTPException:
            pass
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        guild = invite.guild
        is_blocking_invites = await self.config.guild(guild).block_invites()
        cooldown = await self.config.guild(guild).invite_cooldown()
        
        if is_blocking_invites:
            try:
                await invite.delete(reason="Auto-deleting invite due to invite block.")
                embed = discord.Embed(
                    title="Invite Blocked",
                    description=f"**Server:** {guild.name}\n"
                                f"**Inviter:** {invite.inviter.mention} ({invite.inviter.id})\n\n"
                                "This server is currently blocking new invites. Your invite has been deleted.",
                    color=discord.Color.red()
                )
                await invite.inviter.send(embed=embed)
                
                await asyncio.sleep(cooldown)  # Cooldown before another invite can be created
                await self.delete_existing_invites(guild)  # Ensure no new invites exist
            except discord.HTTPException:
                pass
