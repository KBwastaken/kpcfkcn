from .auth import Auth

async def setup(bot):
    await bot.add_cog(Auth(bot))
