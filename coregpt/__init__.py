from .coregpt import CoreGPT

async def setup(bot):
    cog = CoreGPT(bot)
    await bot.add_cog(cog)
