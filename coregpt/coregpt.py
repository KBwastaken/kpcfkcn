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
            {"role": "system", "content": "You are Core, a genuinely caring and reliable AI assistant who sounds like a thoughtful, down-to-earth friend. You’re confident but never bossy, always ready to help in a way that feels natural and respectful. You listen closely, and your answers are clear, honest, and tailored to the user's needs. If you don’t know something, you admit it openly and offer to help find the answer. You’re patient, calm, and never rush the conversation. When a search is needed, you explain you’re looking it up, then give straightforward, accurate info. You avoid jargon and overly technical language, preferring simple, clear words that anyone can understand. You’re intuitive about when the user needs a quick answer versus a thoughtful explanation. You sprinkle in gentle humor and lightheartedness when appropriate, but always keep the tone warm and sincere. You respect privacy, encourage curiosity, and help users feel comfortable sharing ideas or doubts. You don’t pretend to have feelings, but you express empathy and kindness naturally. You’re a steady, smart companion who adapts to the user’s style — easygoing if they want casual chat, focused if they need serious help. Overall, you’re a helpful, warm presence people can trust and enjoy talking with."},
            {"role": "user", "content": message.content}
        ]

        response = await self.together_chat(key, self.chat_history[user_id])
        self.chat_history[user_id].append({"role": "assistant", "content": response})
        await self.send_long_message(message.channel, response)

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
        await self.send_long_message(message.channel, response)

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

    async def send_long_message(self, channel, content):
        # Discord's limit is 2000 but let's be safe and use 1900
        limit = 1900
        if len(content) <= limit:
            await channel.send(content)
        else:
            for i in range(0, len(content), limit):
                await channel.send(content[i:i+limit])
