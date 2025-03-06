# advancedlogs/__init__.py

from .advancedlogs import AdvancedLogs

async def setup(bot):
    """Load the AdvancedLogs cog."""
    await bot.add_cog(AdvancedLogs(bot))
