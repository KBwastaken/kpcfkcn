from .DMlogger import DMLogger  # Adjust to match your cog filename

async def setup(bot):
    await bot.add_cog(DMLogger(bot))
