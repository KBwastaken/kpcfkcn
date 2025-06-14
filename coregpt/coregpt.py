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
            if any(phrase in content_lower for phrase in [
                "can we talk alone", "can we talk privately", "can we talk alone?", "can we talk privately?",
                "talk alone", "talk privately", "talk alone?", "talk privately?"
            ]):
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
                if any(phrase in content_lower for phrase in [
                    "can we talk alone", "can we talk privately", "can we talk alone?", "can we talk privately?",
                    "talk alone", "talk privately", "talk alone?", "talk privately?"
                ]):
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
        if any(phrase in content_lower for phrase in [
            "thank you that's all", "thank you thats all", "thanks that's all", "thanks thats all",
            "that's all", "thats all", "end conversation", "end chat", "stop chat", "close chat"
        ]):
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
                await channel.send("Ending conversation and deleting this channel...")
                # Clean up memory and delete channel
                if guild_id in self.private_channels:
                    self.private_channels[guild_id].pop(user_id, None)
                await asyncio.sleep(3)
                await channel.delete()
            else:
                await channel.send("Okay, let's keep talking!")
            return

        # Continue chat with Together AI
        await self.send_togetherai_response(message, private=True)

    async def start_convo(self, message):
        # Start convo in the channel where "Hey Core" was said
        await self.send_togetherai_response(message, private=False)

    async def continue_convo(self, message):
        # Continue convo (used when replying to bot)
        await self.send_togetherai_response(message, private=False)

    async def send_togetherai_response(self, message, private=False):
        user = message.author
        content = message.content
        channel = message.channel

        # Get user's Together AI key
        api_key = await self.config.user(user).together_api_key()
        if not api_key:
            await channel.send(
                f"{user.mention} You need to set your Together AI API key first using `.gptsetkey [your_api_key]`."
            )
            return

        # Prepare payload
        payload = {
            "prompt": content,
            "model": "llama-3b",
            "max_tokens": 250,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop_sequences": ["###"],
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    "https://api.together.ai/v1/generate",
                    json=payload,
                    headers=headers,
                    timeout=60,
                ) as resp:
                    if resp.status != 200:
                        await channel.send(
                            f"Error from Together AI API: {resp.status} {await resp.text()}"
                        )
                        return
                    data = await resp.json()
            except Exception as e:
                await channel.send(f"Error contacting Together AI API: {e}")
                return

        # Extract generated text
        text = data.get("text") or data.get("response") or ""
        if not text:
            await channel.send("Sorry, no response from Together AI.")
            return

        # Send reply
        await channel.send(text)

