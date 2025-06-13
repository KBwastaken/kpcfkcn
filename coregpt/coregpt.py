import discord
from redbot.core import commands, checks, Config
import aiohttp

class CoreGPT(commands.Cog):
    """ChatGPT integration for Core with conversation memory."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=123456789)
        default_global = {
            "api_key": ""
        }
        self.config.register_global(**default_global)
        # Store chat history per user
        self.histories = {}

    @commands.is_owner()
    @commands.command()
    async def gptstatus(self, ctx):
        """Check if everything is set up correctly."""
        api_key = await self.config.api_key()
        status = "✅ API key set." if api_key else "❌ API key missing."
        await ctx.send(f"CoreGPT status:\n{status}")

    @commands.is_owner()
    @commands.command()
    async def setgptkey(self, ctx, api_key: str):
        """Set your OpenAI API key."""
        await self.config.api_key.set(api_key)
        await ctx.send("API key saved.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        prefixes = ["hey core", "hi core"]
        content = message.content.lower()

        # If it's a new convo with prefix
        if any(content.startswith(p) for p in prefixes):
            user_input = message.content.split(maxsplit=2)
            if len(user_input) < 3:
                await message.channel.send("What do you want me to do?")
                return

            prompt = message.content[len(user_input[0]) + 1:]
            await self.handle_gpt(message, prompt)

        # If it's a reply to the bot
        elif message.reference:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author.id == self.bot.user.id:
                    await self.handle_gpt(message, message.content)
            except Exception:
                pass  # fail silently

    async def handle_gpt(self, message, user_input):
        api_key = await self.config.api_key()
        if not api_key:
            await message.channel.send("API key not set. Ask the bot owner to use [p]setgptkey.")
            return

        user_id = message.author.id
        history = self.histories.get(user_id, [])
        history.append({"role": "user", "content": user_input})

        # Keep last 10 messages to limit context size
        history = history[-10:]

        async with aiohttp.ClientSession() as session:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            json_data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "system", "content": "You are a helpful assistant."}] + history
            }

            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    await message.channel.send(f"Error: {resp.status}")
                    return
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"]

                history.append({"role": "assistant", "content": reply})
                self.histories[user_id] = history  # Save updated history

                await message.channel.send(reply)
