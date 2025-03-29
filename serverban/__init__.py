from .serverban import ServerBan

async def setup(bot):
    await bot.add_cog(ServerBan(bot))
