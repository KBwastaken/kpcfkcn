import discord
from redbot.core import commands, Config
import asyncio
import logging

log = logging.getLogger("red.globalban")

class GlobalBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(ban_list={})
        self.ban_update_task = self.bot.loop.create_task(self.ban_update_loop())
        self.ban_sync_task = self.bot.loop.create_task(self.ban_sync_loop())
    
    async def ban_update_loop(self):
        await self.bot.wait_until_ready()
        while True:
            log.info("Starting 6-hour global ban list update...")
            await self.globalbanupdatelist(None)
            log.info("Global ban list update complete. Next update in 6 hours.")
            await asyncio.sleep(21600)  # 6 hours
    
    async def ban_sync_loop(self):
        await self.bot.wait_until_ready()
        while True:
            log.info("Starting 12-hour global ban sync...")
            await self.sync_bans()
            log.info("Global ban sync complete. Next sync in 12 hours.")
            await asyncio.sleep(43200)  # 12 hours
    
    async def sync_bans(self):
        ban_list = await self.config.ban_list()
        for guild in self.bot.guilds:
            log.info(f"Syncing bans for {guild.name}...")
            count = 0
            for user_id in ban_list.keys():
                user = discord.Object(id=int(user_id))
                try:
                    await guild.ban(user, reason="Global ban sync")
                    count += 1
                    if count % 20 == 0:
                        log.info(f"{count} bans synced in {guild.name}")
                    await asyncio.sleep(1)  # Prevent rate limits
                except discord.Forbidden:
                    log.warning(f"No permission to ban in {guild.name}")
                except discord.HTTPException as e:
                    log.error(f"Error banning in {guild.name}: {e}")
            log.info(f"All bans synced in {guild.name} ({count} total).")

    @commands.command()
    async def bansync(self, ctx):
        """Manually sync global bans across all servers."""
        await self.sync_bans()
        await ctx.send("Ban sync complete.")
    
    @commands.command()
    async def globaltotalbans(self, ctx):
        """Show total number of globally banned users."""
        ban_list = await self.config.ban_list()
        await ctx.send(f"{len(ban_list)} users have been globally banned.")
    
    @commands.command()
    async def globalbanlist(self, ctx):
        """Send the global ban list."""
        ban_list = await self.config.ban_list()
        if not ban_list:
            await ctx.send("The global ban list is empty.")
            return
        
        content = "\n".join([f"{uid}: {data['reason']}" for uid, data in ban_list.items()])
        if len(content) > 1500:
            with open("globalbanlist.txt", "w") as f:
                f.write(content)
            await ctx.send("Global ban list is too large. Sending as a file.", file=discord.File("globalbanlist.txt"))
        else:
            await ctx.send(f"```{content}```")
    
    @commands.command()
    async def globalbanlistwipe(self, ctx):
        """Wipe the entire global ban list."""
        msg = await ctx.send("Are you sure you want to wipe the global ban list? React with ✅ to confirm.")
        await msg.add_reaction("✅")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅"
        
        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Wipe request timed out.")
            return
        
        await self.config.ban_list.set({})
        await ctx.send("Global ban list wiped.")
        log.info("Global ban list has been wiped.")
    
    @commands.command()
    async def globalbanupdatelist(self, ctx):
        """Fetch all bans from all servers and update the global list."""
        log.info("Updating global ban list from the current servers...")
        banned_users = {}
        
        for guild in self.bot.guilds:
            log.info(f"Fetching bans from the server: {guild.name}")
            try:
                count = 0
                async for ban_entry in guild.bans():
                    user_id = str(ban_entry.user.id)
                    if user_id not in banned_users:
                        banned_users[user_id] = {
                            "reason": ban_entry.reason or "No reason provided",
                            "banned_by": "Unknown"
                        }
                        count += 1
                        if count % 5 == 0:
                            log.info(f"Still fetching bans... {count} users added so far from {guild.name}.")
                    await asyncio.sleep(1)  # Prevent rate limits
                log.info(f"Fetched {len(banned_users)} bans from {guild.name}")
            except discord.HTTPException as e:
                log.error(f"Error fetching bans from {guild.name}: {e}")
                if ctx:
                    await ctx.send(f"An error occurred while fetching bans from {guild.name}.")
        
        await self.config.ban_list.set(banned_users)
        log.info(f"All fetched, list updated. Total bans: {len(banned_users)}")
        if ctx:
            await ctx.send(f"Global ban list updated. {len(banned_users)} bans recorded.")
    
    @commands.command()
    async def globalban(self, ctx, user: discord.User, *, reason="No reason provided"):
        """Ban a user globally"""
        ban_list = await self.config.ban_list()
        if str(user.id) in ban_list:
            await ctx.send("User is already globally banned.")
            return
        
        ban_list[str(user.id)] = {"reason": reason, "banned_by": ctx.author.id}
        await self.config.ban_list.set(ban_list)
        
        for guild in self.bot.guilds:
            try:
                await guild.ban(user, reason=f"Global ban: {reason}")
            except discord.Forbidden:
                log.warning(f"No permission to ban {user} in {guild.name}")
            except discord.HTTPException as e:
                log.error(f"Failed to ban {user} in {guild.name}: {e}")
        
        await ctx.send(f"{user} has been globally banned.")
        log.info(f"{user} globally banned by {ctx.author} for: {reason}")

async def setup(bot):
    await bot.add_cog(GlobalBan(bot))
