from redbot.core import commands
import random

class TweakingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Initializes the bot instance for the cog to use

    @commands.command()
    async def tweaking(self, ctx):
        responses = [
            f"Oh no! {ctx.author.mention} is TWEAKING! Someone help them out before they break something!",
            f"Uh oh! Looks like {ctx.author.mention} is TWEAKING. Proceed with caution!",
            f"Yikes! {ctx.author.mention} is TWEAKING! Hold on tight, this is about to get wild!",
            f"{ctx.author.mention} is in full tweak mode! Get ready for the chaos!"
        ]
        
        response = random.choice(responses)
        
        # Send the response along with the GIF link
        await ctx.send(f"{response} \n\nhttps://tenor.com/view/skeleton-banging-fist-on-ground-agony-anguish-pain-suffering-gif-10047053495593873096")

def setup(bot):
    bot.add_cog(TweakingCog(bot))
