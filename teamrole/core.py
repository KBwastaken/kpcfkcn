from redbot.core import commands, Config

class TeamRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_global(team_members=[])

    @commands.command()
    async def test(self, ctx):
        """Test command to verify cog works"""
        await ctx.send("✅ Cog loaded successfully!")
