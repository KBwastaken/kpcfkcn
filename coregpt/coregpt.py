import discord
from redbot.core import commands, Config
import aiohttp

class CoreGPT(commands.Cog):
    """CoreGPT: Talk to Together AI's free Llama-3, with convo threading."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_user = {"together_api_key": None}
        self.config.register_user(**default_user)
        self.chat_history = {}  # Keep short convo per user

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

        # New convo trigger: "hey core" or "hi core"
        if message.content.lower().startswith(("hey core", "hi core")):
            await self.start_convo(message)
            return

        # Continuation: user replies to the bot's message
        if message.reference:
            ref = await message.channel.fetch_message(message.reference.message_id)
            if ref and ref.author.id == self.bot.user.id:
                await self.continue_convo(message)

    async def start_convo(self, message):
        key = await self.config.user(message.author).together_api_key()
        if not key:
            await message.channel.send("Please set your Together AI API key using `.gptsetkey` first.")
            return

        user_id = message.author.id
        self.chat_history[user_id] = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message.content}
        ]

        response = await self.together_chat(key, self.chat_history[user_id])
        self.chat_history[user_id].append({"role": "assistant", "content": response})
        await message.channel.send(response)

    async def continue_convo(self, message):
        key = await self.config.user(message.author).together_api_key()
        if not key:
            await message.channel.send("Please set your Together AI API key using `.gptsetkey` first.")
            return

        user_id = message.author.id
        if user_id not in self.chat_history:
            # No prior context, treat as fresh
            await self.start_convo(message)
            return

        self.chat_history[user_id].append({"role": "user", "content": message.content})
        response = await self.together_chat(key, self.chat_history[user_id])
        self.chat_history[user_id].append({"role": "assistant", "content": response})
        await message.channel.send(response)

    async def together_chat(self, api_key, messages):
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": "meta-llama/Llama-3-8b-chat-hf",
            "messages": messages
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Error: {resp.status} - {await resp.text()}"
