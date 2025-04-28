from .rolemanager import RoleManager  # No change, this should be correct

async def setup(bot):
    cog = RoleManager(bot)
    await bot.add_cog(cog)
    await cog.sync_slash_commands()
