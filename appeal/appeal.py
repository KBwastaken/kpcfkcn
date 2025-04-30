from redbot.core import commands

class Appeal(commands.Cog):
    """Appeal command cog."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def appeal(self, ctx):
        """Sends the appeal form link."""
        await ctx.send(
            "Oopsie whoopsie, got yourself or a friend of yours banned?\n\n"
            "Fix it here:\n"
            "https://forms.gle/gR6f9iaaprASRgyP9"
        )
    @commands.command()
    async def appeals(self, ctx):
        """Sends the appeal form link."""
        await ctx.send(
            "Oopsie whoopsie, got yourself or a friend of yours banned?\n\n"
            "Fix it here:\n"
            "https://forms.gle/gR6f9iaaprASRgyP9"
        )
