from .rainbowpooper import RainbowPooper

async def setup(bot):
    await bot.add_cog(RainbowPooper(bot))
