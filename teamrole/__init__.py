from .core import TeamRole

def setup(bot):
    print("[TeamRole] Setting up cog...")  # Debugging statement
    cog = TeamRole(bot)
    bot.add_cog(cog)
    print("[TeamRole] Cog loaded successfully!")  # Debugging statement
