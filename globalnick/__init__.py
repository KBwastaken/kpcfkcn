from .globalnick import GlobalNick

async def setup(bot):
    await bot.add_cog(GlobalNick(bot))
