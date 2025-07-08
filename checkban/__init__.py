from redbot.core import commands
from .checkban import CheckBan

async def setup(bot):
    await bot.add_cog(CheckBan(bot))
