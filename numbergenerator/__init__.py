from .numbergenerator import NumberGeneratorCog

def setup(bot):
    bot.add_cog(NumberGeneratorCog(bot))
