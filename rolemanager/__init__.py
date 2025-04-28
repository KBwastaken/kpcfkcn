from .rolemanager import RoleManager

async def setup(bot):
    cog = RoleManager(bot)
    await bot.add_cog(cog)
