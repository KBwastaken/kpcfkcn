from .botwhitelist import BotWhitelist

__red_end_user_data_statement__ = "This cog does not store any persistent data."

async def setup(bot):
    await bot.add_cog(BotWhitelist(bot))  # Await add_cog to avoid the warning/error
