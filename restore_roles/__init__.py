from .restoreroles import RestoreRoles

async def setup(bot):
    await bot.add_cog(RestoreRoles(bot))
