import openai
from redbot.core import commands, Config
import discord

class CoreGPT(commands.Cog):
    """A simple ChatGPT Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {"api_key": ""}
        self.config.register_global(**default_global)

    @commands.group()
    async def coregpt(self, ctx):
        """ChatGPT Cog"""
        pass

    @coregpt.command()
    async def setkey(self, ctx, key: str):
        """Set your OpenAI API key"""
        await self.config.api_key.set(key)
        await ctx.send("API key set successfully.")

    @commands.command()
    async def ask(self, ctx, *, prompt: str):
        """Ask ChatGPT something"""
        api_key = await self.config.api_key()
        if not api_key:
            await ctx.send("API key not set. Use `[p]coregpt setkey YOUR_API_KEY` first.")
            return

        openai.api_key = api_key

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content
            await ctx.send(answer)
        except Exception as e:
            await ctx.send(f"Error: {e}")
