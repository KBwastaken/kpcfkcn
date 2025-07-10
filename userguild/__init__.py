from .userguild import UserTokenGuildChecker

async def setup(bot):
    await bot.add_cog(UserTokenGuildChecker(bot))
