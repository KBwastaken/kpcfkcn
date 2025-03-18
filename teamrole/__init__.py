"""TeamRole cog for Red Discord Bot."""  
from .core import TeamRole  

async def setup(bot):  
    await bot.add_cog(TeamRole(bot))
