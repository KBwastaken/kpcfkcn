from .tweaking import TweakingCog

async def setup(bot):
    await bot.add_cog(TweakingCog(bot))
