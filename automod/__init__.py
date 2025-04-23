from .automod import AutoMod

async def setup(bot):
    cog = AutoMod(bot)
    await bot.add_cog(cog)
