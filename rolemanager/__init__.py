# rolemanager/__init__.py
from .rolemanager import RoleManager

async def setup(bot):
    cog = RoleManager(bot)
    await bot.add_cog(cog)
    await cog.sync_slash_commands()
