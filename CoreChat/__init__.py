from .corechat import CoreChat

async def setup(bot):
    await bot.add_cog(CoreChat(bot))
