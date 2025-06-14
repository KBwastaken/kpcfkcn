import discord
from discord.ext import commands
from redbot.core import Config
import aiohttp
import asyncio

class CoreGPT(commands.Cog):
    """CoreGPT: Talk to Together AI's free Llama-3, with convo threading and private chats."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_user = {"together_api_key": None}
        default_guild = {"private_category": None}
        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)

        self.chat_history = {}  # user_id -> list of messages
        self.private_channels = {}  # guild_id -> {user_id: channel_id}

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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
async def gptsetcategory(self, ctx, category: discord.CategoryChannel = None):
    async def gptsetcategory(self, ctx, category: discord.CategoryChannel = None):
        """Set the category for private GPT channels in this server."""
        if not category:
            await self.config.guild(ctx.guild).private_category.set(None)
            await ctx.send("Private chat category unset.")
            return
        if category.guild != ctx.guild:
            await ctx.send("Please provide a category from this server.")
            return
        await self.config.guild(ctx.guild).private_category.set(category.id)
        await ctx.send(f"Private chat category set to: {category.name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Check if message is in a private chat channel created by bot
        if message.guild:
            guild_id = message.guild.id
            user_id = message.author.id
            private_chs = self.private_channels.get(guild_id, {})
            if user_id in private_chs and private_chs[user_id] == message.channel.id:
                await self.handle_private_chat(message)
                return

        content_lower = message.content.lower()

        # Detect "hey core" start of message
        if content_lower.startswith("hey core"):
            # If "can we talk alone" or "can we talk privately" or "can we talk"
            if any(phrase in content_lower for phrase in ["can we talk alone", "can we talk privately", "can we talk alone?","can we talk privately?","talk alone","talk privately","talk alone?","talk privately?"]):
                # Start private channel flow
                if not message.guild:
                    await message.channel.send("This command only works in servers.")
                    return
                await self.create_private_channel(message)
                return
            else:
                # normal core convo start
                await self.start_convo(message)
                return

        # If message is a reply to any bot message and contains "can we talk alone" etc
        if message.reference:
            try:
                ref = await message.channel.fetch_message(message.reference.message_id)
            except (discord.NotFound, discord.Forbidden):
                ref = None
            if ref and ref.author.id == self.bot.user.id:
                # check content for private chat trigger
                if any(phrase in content_lower for phrase in ["can we talk alone", "can we talk privately", "can we talk alone?","can we talk privately?","talk alone","talk privately","talk alone?","talk privately?"]):
                    if not message.guild:
                        await message.channel.send("This command only works in servers.")
                        return
                    await self.create_private_channel(message)
                    return
                else:
                    # continue normal convo
                    await self.continue_convo(message)
                    return

        # If message is in DM or no private triggers, just ignore

    async def create_private_channel(self, message):
        guild = message.guild
        user = message.author
        category_id = await self.config.guild(guild).private_category()
        if not category_id:
            await message.channel.send("No private chat category set in this server. Please contact kkkkayaaaaa.")
            return

        category = guild.get_channel(category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            await message.channel.send("The private chat category is invalid or missing. Please contact kkkkayaaaaa.")
            return

        # Check if user already has a private channel in this guild
        if guild.id not in self.private_channels:
            self.private_channels[guild.id] = {}
        if user.id in self.private_channels[guild.id]:
            existing_ch = guild.get_channel(self.private_channels[guild.id][user.id])
            if existing_ch:
                await message.channel.send(f"{user.mention} You already have a private chat channel: {existing_ch.mention}")
                return
            else:
                # channel missing, remove from dict
                del self.private_channels[guild.id][user.id]

        # Create private channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        # Make sure role "KCN | Team" can view and send messages but not mention @everyone
        role = discord.utils.get(guild.roles, name="KCN | Team")
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        else:
            # We still create channel but no role overwrite
            pass

        channel_name = f"core-chat-{user.name}".lower()
        channel = await category.create_text_channel(channel_name, overwrites=overwrites, reason="Private GPT chat channel")

        # Save channel id
        self.private_channels[guild.id][user.id] = channel.id

        # Send intro message with ping, mention-only setup
        await channel.send(
            f"{user.mention} This is your private chat with Core. If you ever want to end our conversation, just say 'thank you that's all' or something similar and I'll ask for confirmation and then delete this channel."
        )

        await message.channel.send(f"{user.mention} Your private chat channel has been created: {channel.mention}")

    async def handle_private_chat(self, message):
        user = message.author
        channel = message.channel
        guild = message.guild
        user_id = user.id
        guild_id = guild.id

        # Make sure channel is mention-only (override @everyone and here)
        overwrites = channel.overwrites_for(guild.default_role)
        if overwrites.view_channel != False or overwrites.send_messages != False:
            await channel.set_permissions(guild.default_role, view_channel=False, send_messages=False)

        # Detect serious distress phrases
        warning_phrases = [
            "i want to kms",
            "i don't want this anymore",
            "i dont want this anymore",
            "i'm being abused",
            "im being abused",
            "i feel hopeless",
            "i can't take this",
            "i cant take this",
            "i want to die",
            "i hate myself",
            "i'm so alone",
            "im so alone",
            "i want to end it",
            "i can't do this anymore",
            "im struggling",
            "i'm being bullied",
            "im bullied",
            "being bullied",
            "they keep bullying me",
            "they're bullying me",
            "i feel worthless",
            "nobody cares about me",
            "i feel like giving up",
            "i'm overwhelmed",
            "im overwhelmed",
            "please help me",
            "i feel trapped",
            "i don't see a way out",
            "i dont see a way out",
            "i am depressed",
            "im depressed",
            "no one loves me",
            "i don't want to live",
            "im hurting",
            "i'm hurting",
            "suicidal",
            "i feel broken",
        ]

        content_lower = message.content.lower()

        if any(phrase in content_lower for phrase in warning_phrases):
            await channel.send(
                f"{user.mention}, it sounds like you're really struggling right now. "
                "Do you want me to ping a real human to assist you? Please reply with 'yes' or 'no'."
            )

            def comfort_check(m):
                return (
                    m.author.id == user.id
                    and m.channel.id == channel.id
                    and m.content.lower() in ["yes", "no"]
                )

            try:
                reply = await self.bot.wait_for("message", check=comfort_check, timeout=60)
            except asyncio.TimeoutError:
                await channel.send("No response received. I'm here if you want to talk more.")
                return

            if reply.content.lower() == "yes":
                role = discord.utils.get(guild.roles, name="KCN | Team")
                if role:
                    await channel.send(f"{role.mention}, {user.mention} needs assistance.")
                    await channel.send("I've pinged the KCN | Team for you.")
                else:
                    await channel.send(
                        "Sorry, I couldn't find the 'KCN | Team' role to ping. Please reach out directly."
                    )
            else:
                await channel.send("Okay, I'm here to listen if you want to keep talking.")
            return

        # Detect "thank you that's all" or similar to end convo
        if any(phrase in content_lower for phrase in ["thank you that's all", "thank you thats all", "thanks that's all", "thanks thats all", "that's all", "thats all", "end conversation", "end chat", "stop chat", "close chat"]):
            await channel.send(f"{user.mention} Are you sure you want to end this conversation? Please reply 'yes' or 'no'.")

            def end_check(m):
                return (
                    m.author.id == user.id
                    and m.channel.id == channel.id
                    and m.content.lower() in ["yes", "no"]
                )

            try:
                reply = await self.bot.wait_for("message", check=end_check, timeout=30)
            except asyncio.TimeoutError:
                await channel.send("No response received. Continuing the conversation.")
                return

            if reply.content.lower() == "yes":
                await channel.send("Okay, ending the conversation and deleting this channel. Take care!")
                # Remove from dict
                if guild_id in self.private_channels and user_id in self.private_channels[guild_id]:
                    del self.private_channels[guild_id][user_id]
                await channel.delete()
                return
            else:
                await channel.send("Glad to keep talking with you.")

            return

        # Normal GPT continuation in private chat
        if guild_id not in self.chat_history:
            self.chat_history[guild_id] = {}
        if user_id not in self.chat_history[guild_id]:
            # Start fresh system prompt for private chat
            self.chat_history[guild_id][user_id] = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": message.content},
            ]
        else:
            self.chat_history[guild_id][user_id].append({"role": "user", "content": message.content})

        key = await self.config.user(user).together_api_key()
        if not key:
            await channel.send(f"{user.mention} Please set your Together AI API key using `.gptsetkey` first.")
            return

        response = await self.together_chat(key, self.chat_history[guild_id][user_id])
        self.chat_history[guild_id][user_id].append({"role": "assistant", "content": response})
        await self.send_long_message(channel, response)

    async def start_convo(self, message):
        user = message.author
        user_id = user.id
        if user_id not in self.chat_history:
            self.chat_history[user_id] = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": message.content},
            ]
        else:
            self.chat_history[user_id].append({"role": "user", "content": message.content})

        key = await self.config.user(user).together_api_key()
        if not key:
            await message.channel.send(f"{user.mention} Please set your Together AI API key using `.gptsetkey` first.")
            return

        response = await self.together_chat(key, self.chat_history[user_id])
        self.chat_history[user_id].append({"role": "assistant", "content": response})
        await self.send_long_message(message.channel, response)

    async def continue_convo(self, message):
        user = message.author
        user_id = user.id
        if user_id not in self.chat_history:
            await self.start_convo(message)
            return
        self.chat_history[user_id].append({"role": "user", "content": message.content})

        key = await self.config.user(user).together_api_key()
        if not key:
            await message.channel.send(f"{user.mention} Please set your Together AI API key using `.gptsetkey` first.")
            return

        response = await self.together_chat(key, self.chat_history[user_id])
        self.chat_history[user_id].append({"role": "assistant", "content": response})
        await self.send_long_message(message.channel, response)

    async def together_chat(self, api_key, messages):
        url = "https://api.together.xyz/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        json_data = {
            "model": "llama-3-chat",
            "messages": messages,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                if resp.status != 200:
                    return f"API Error: {resp.status}"
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "No response")

    def get_system_prompt(self):
        return (
            "You are CoreGPT, an AI assistant designed to help users with friendly, helpful responses. "
            "Keep conversations warm, understanding, and concise."
        )

    async def send_long_message(self, channel, content):
        if len(content) <= 2000:
            await channel.send(content)
            return
        # Split content on newlines first to keep paragraphs
        parts = content.split("\n")
        buffer = ""
        for part in parts:
            if len(buffer) + len(part) + 1 > 2000:
                await channel.send(buffer)
                buffer = ""
            buffer += part + "\n"
        if buffer:
            await channel.send(buffer)

