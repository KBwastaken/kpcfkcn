from .core import TeamRole

def setup(bot):
    cog = TeamRole(bot)
    bot.add_cog(cog)
