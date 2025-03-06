# advancedlogs/__init__.py

from .advancedlogs import AdvancedLogs

def setup(bot):
    """Load the AdvancedLogs cog."""
    bot.add_cog(AdvancedLogs(bot))
