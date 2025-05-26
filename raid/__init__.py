from .raid import Raid

async def setup(bot):
    await bot.add_cog(Raid(bot))
