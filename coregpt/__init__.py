from .coregpt import CoreGPT

async def setup(bot):
    await bot.add_cog(CoreGPT(bot))
