from .core import kcnprotect
async def setup(bot):  
    await bot.add_cog(kcnprotect(bot))
