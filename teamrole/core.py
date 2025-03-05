from redbot.core import commands

class TeamRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def test(self, ctx):
        await ctx.send("✅ Cog works!")
