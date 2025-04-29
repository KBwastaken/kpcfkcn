from redbot.core import commands

class Appeal(commands.Cog):
    """Appeal command cog."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def appeal(self, ctx):
        """Sends the appeal form link."""
        await ctx.send("https://forms.gle/gR6f9iaaprASRgyP9")
