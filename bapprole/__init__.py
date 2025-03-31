from .core import bapprole
async def setup(bot):  
    await bot.add_cog(bapprole(bot))
