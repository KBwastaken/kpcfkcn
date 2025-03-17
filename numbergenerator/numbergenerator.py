from redbot.core import commands
import random

class NumberGeneratorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def number(self, ctx, *args):
        """Generates a random number based on provided arguments."""
        
        if len(args) == 1:
            # If only one argument is given, generate a number between 1 and that number
            try:
                end = int(args[0])
                if end < 1:
                    await ctx.send("Please provide a positive number.")
                    return
                number = random.randint(1, end)
                await ctx.send(f"{ctx.author.mention}, your random number between 1 and {end} is: {number}")
            except ValueError:
                await ctx.send("Oops! Please provide a valid number.")
        
        elif len(args) == 2:
            # If two arguments are given, generate a number between the two
            try:
                start = int(args[0])
                end = int(args[1])
                if start >= end:
                    await ctx.send("The start value must be less than the end value.")
                    return
                number = random.randint(start, end)
                await ctx.send(f"{ctx.author.mention}, your random number between {start} and {end} is: {number}")
            except ValueError:
                await ctx.send("Oops! Please provide valid numbers.")
        
        else:
            await ctx.send("Please provide one or two numbers as arguments.")

def setup(bot):
    bot.add_cog(NumberGeneratorCog(bot))
