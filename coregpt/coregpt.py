import discord
from redbot.core import commands, Config
import aiohttp

class CoreGPT(commands.Cog):
    """CoreGPT: Talk to Together AI's free Llama-3."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_user = {"together_api_key": None}
        self.config.register_user(**default_user)

    @commands.command()
    async def gptsetkey(self, ctx, key):
        """Set your Together AI API key."""
        await self.config.user(ctx.author).together_api_key.set(key)
        await ctx.send("Your Together AI API key has been saved.")

    @commands.command()
    async def gptstatus(self, ctx):
        """Check your Together AI API key status."""
        key = await self.config.user(ctx.author).together_api_key()
        if key:
            await ctx.send("Together AI API key is set.")
        else:
            await ctx.send("No Together AI API key found. Use `.gptsetkey` to set it.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.lower().startswith(("hey core", "hi core")):
            key = await self.config.user(message.author).together_api_key()
            if not key:
                await message.channel.send("Please set your Together AI API key using `.gptsetkey` first.")
                return

            prompt = message.content
            response = await self.together_chat(key, prompt)
            await message.channel.send(response)

    async def together_chat(self, api_key, prompt):
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": "meta-llama/Llama-3-8b-chat-hf",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Error: {resp.status} - {await resp.text()}"
