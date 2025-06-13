import discord
from redbot.core import commands, checks, Config
import aiohttp

class CoreGPT(commands.Cog):
    """Hugging Face integration for Core with conversation memory."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=123456789)
        default_global = {
            "hf_token": ""
        }
        self.config.register_global(**default_global)
        self.histories = {}

    @commands.is_owner()
    @commands.command()
    async def gptstatus(self, ctx):
        """Check if everything is set up correctly."""
        hf_token = await self.config.hf_token()
        status = "✅ HF token set." if hf_token else "❌ HF token missing."
        await ctx.send(f"CoreGPT status:\n{status}")

    @commands.is_owner()
    @commands.command()
    async def sethftoken(self, ctx, hf_token: str):
        """Set your Hugging Face token."""
        await self.config.hf_token.set(hf_token)
        await ctx.send("Hugging Face token saved.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        prefixes = ["hey core", "hi core"]
        content = message.content.lower()

        if any(content.startswith(p) for p in prefixes):
            user_input = message.content.split(maxsplit=2)
            if len(user_input) < 3:
                await message.channel.send("What do you want me to do?")
                return

            prompt = message.content[len(user_input[0]) + 1:]
            await self.handle_gpt(message, prompt)

        elif message.reference:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author.id == self.bot.user.id:
                    await self.handle_gpt(message, message.content)
            except Exception:
                pass

    async def handle_gpt(self, message, user_input):
        hf_token = await self.config.hf_token()
        if not hf_token:
            await message.channel.send("Hugging Face token not set. Use [p]sethftoken.")
            return

        user_id = message.author.id
        history = self.histories.get(user_id, [])
        history.append(user_input)

        # Keep last 5 lines to limit prompt size
        short_history = history[-5:]
        prompt = "\n".join(short_history)

        async with aiohttp.ClientSession() as session:
            url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
            headers = {
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json"
            }
            json_data = {
                "inputs": prompt
            }

            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    await message.channel.send(f"Error: {resp.status}")
                    return
                data = await resp.json()
                reply = data[0]["generated_text"].split(prompt, 1)[-1].strip()
                history.append(reply)
                self.histories[user_id] = history
                await message.channel.send(reply)
