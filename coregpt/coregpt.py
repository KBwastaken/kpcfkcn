import discord
from redbot.core import commands, checks
import aiohttp
import asyncio

class CoreGPT(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "http://localhost:5000/api/v1/generate"  # Change if needed
        self.session = aiohttp.ClientSession()
        self.conversations = {}  # To keep track of conversation history per user/message

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Check if message starts with "Hey core" or "Hi core" (case insensitive)
        content_lower = message.content.lower()
        if content_lower.startswith("hey core") or content_lower.startswith("hi core"):
            # Remove prefix and any leading/trailing whitespace
            user_input = message.content[len(message.content.split()[0]) + 1:].strip()

            if not user_input:
                await message.channel.send("Yes? How can I help?")
                return

            await self.handle_gpt_response(message, user_input)

        # If user replies to bot message, continue conversation
        elif message.reference:
            ref_msg = message.reference.resolved
            if ref_msg and ref_msg.author == self.bot.user:
                # Use conversation memory key (e.g. channel id + author id)
                conv_key = f"{message.channel.id}-{message.author.id}"
                history = self.conversations.get(conv_key, [])
                user_input = message.content.strip()

                # Append user input to history
                history.append({"role": "user", "content": user_input})

                await self.handle_gpt_response(message, user_input, history=history)

    async def handle_gpt_response(self, message, prompt, history=None):
        # Build payload for your local AI (adjust if your API expects different)
        payload = {
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.7,
        }

        # You can implement conversation memory here if your API supports it
        if history:
            # Example: concatenate history with prompt
            full_prompt = ""
            for entry in history:
                full_prompt += f"{entry['role']}: {entry['content']}\n"
            full_prompt += f"user: {prompt}\n"
            payload["prompt"] = full_prompt

        try:
            async with self.session.post(self.api_url, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    await message.channel.send(f"Oops, AI server returned error {resp.status}")
                    return
                data = await resp.json()
                # Extract the generated text depending on your API
                # Here we assume response format: {"results": [{"text": "..."}]}
                text = data.get("results", [{}])[0].get("text", None)
                if not text:
                    await message.channel.send("Hmm, I didn’t get a response from AI.")
                    return

                await message.channel.send(text.strip())

                # Save conversation history
                conv_key = f"{message.channel.id}-{message.author.id}"
                history = history or []
                history.append({"role": "assistant", "content": text.strip()})
                self.conversations[conv_key] = history

        except asyncio.TimeoutError:
            await message.channel.send("AI server took too long to respond.")
        except Exception as e:
            await message.channel.send(f"Something went wrong: {e}")

    @commands.command()
    @checks.is_owner()
    async def gptstatus(self, ctx):
        """Check if AI server is reachable and working."""
        try:
            async with self.session.get(f"{self.api_url}/status", timeout=10) as resp:
                if resp.status == 200:
                    await ctx.send("AI server is up and running!")
                else:
                    await ctx.send(f"AI server responded with status code {resp.status}")
        except Exception as e:
            await ctx.send(f"Could not reach AI server: {e}")
