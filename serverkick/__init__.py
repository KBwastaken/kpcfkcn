from .serverkick import ServerKick

async def setup(bot):
    await bot.add_cog(ServerKick(bot))
