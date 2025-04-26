import discord
from redbot.core import commands, Config
import aiohttp

class CoreChat(commands.Cog):
    """Chatbot using OpenAI's ChatGPT"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {
            "api_token": None
        }
        self.config.register_guild(**default_guild)

    @commands.command()
    @commands.admin_or_permissions(manage_guild=True)
    async def aiset(self, ctx, *, token: str):
        """Set the OpenAI API token."""
        await self.config.guild(ctx.guild).api_token.set(token)
        await ctx.send("API token has been set.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.content.lower().startswith("hey core"):
            return

        token = await self.config.guild(message.guild).api_token()
        if not token:
            await message.channel.send("API token is not set. Please use `.aiset token <token>`.")
            return

        prompt = message.content[len("hey core"):].strip()
        if not prompt:
            await message.channel.send("Please provide a message after `Hey core`.")
            return

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    await message.channel.send(f"API Error: {error}")
                    return
                response = await resp.json()

        try:
            reply = response["choices"][0]["message"]["content"]
            await message.channel.send(reply)
        except (KeyError, IndexError):
            await message.channel.send("Error parsing the response from OpenAI.")

async def setup(bot):
    await bot.add_cog(CoreChat(bot))
