from .auth import AuthCog

async def setup(bot):
    await bot.add_cog(AuthCog(bot))
