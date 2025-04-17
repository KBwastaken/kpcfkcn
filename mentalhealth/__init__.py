from .mentalhealth import MentalHealth

async def setup(bot):
    await bot.add_cog(MentalHealth(bot))
