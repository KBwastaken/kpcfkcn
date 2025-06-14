from openai import OpenAI
from redbot.core import commands, Config

class CoreGPT(commands.Cog):
    """A ChatGPT Cog for Red"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210)
        default_global = {"api_key": "", "model": "gpt-3.5-turbo"}
        self.config.register_global(**default_global)
        self.client = None

    async def get_client(self):
        if not self.client:
            api_key = await self.config.api_key()
            self.client = OpenAI(api_key=api_key)
        return self.client

    @commands.command()
    async def gptsetkey(self, ctx, key: str):
        """Set your OpenAI API key"""
        await self.config.api_key.set(key)
        self.client = None
        await ctx.send("✅ API key set!")

    @commands.command()
    async def gptstatus(self, ctx):
        """Show GPT status"""
        api_key = await self.config.api_key()
        model = await self.config.model()
        if api_key:
            masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        else:
            masked = "Not set"

        msg = f"**API Key:** `{masked}`\n**Model:** `{model}`"
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        content = message.content.lower()
        if content.startswith("hey core") or content.startswith("hi core"):
            api_key = await self.config.api_key()
            if not api_key:
                await message.channel.send("API key not set. Use `.gptsetkey YOUR_API_KEY` first.")
                return

            user_input = message.content.split(maxsplit=2)
            if len(user_input) < 2:
                await message.channel.send("Please say something after `hey core` or `hi core`.")
                return

            prompt = message.content[len(user_input[0]) :].strip()

            try:
                client = await self.get_client()
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                answer = response.choices[0].message.content
                await message.channel.send(answer)
            except Exception as e:
                await message.channel.send(f"Error: {e}")
