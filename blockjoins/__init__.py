from .blockjoins import BlockJoins

async def setup(bot):
    await bot.add_cog(BlockJoins(bot))
