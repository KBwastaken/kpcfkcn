from .appeal import Appeal

async def setup(bot):
    await bot.add_cog(Appeal(bot))
