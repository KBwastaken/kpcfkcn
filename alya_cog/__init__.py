from .alya_cog import AlyaCog

async def setup(bot):
    await bot.add_cog(AlyaCog(bot))
