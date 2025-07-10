from .guildtracker import GuildTracker

async def setup(bot):
    await bot.add_cog(GuildTracker(bot))
