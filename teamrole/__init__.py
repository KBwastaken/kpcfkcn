from .teamrole import TeamRole

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
