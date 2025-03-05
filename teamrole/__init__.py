from .core import TeamRole

def setup(bot):
    bot.add_cog(TeamRole(bot))  # Sync setup (NO ASYNC/AWAIT)
