from .numbergenerator import NumberGeneratorCog

async def setup(bot):
    await bot.add_cog(NumberGeneratorCog(bot))
