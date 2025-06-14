import discord
from redbot.core import commands, Config
import aiohttp
import asyncio

class CoreGPT(commands.Cog):
    """CoreGPT: Talk to Together AI's free Llama-3, with convo threading, plus private chats."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_user = {"together_api_key": None}
        default_guild = {"private_category": None}
        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)
        self.chat_history = {}  # user_id: messages list for convo memory
        self.private_channels = {}  # channel_id: user_id for private chats

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
    @commands.admin()
    async def gptsetcategory(self, ctx, category: discord.CategoryChannel):
        """Set the category for private CoreGPT chats."""
        await self.config.guild(ctx.guild).private_category.set(category.id)
        await ctx.send(f"Private chat category set to: {category.name}")

    async def detect_distress(self, api_key, messages):
        # Ask the AI if the user seems in emotional distress or crisis
        check_messages = messages + [
            {
                "role": "system",
                "content": (
                    "Based on the conversation, does the user seem to be in emotional distress or crisis? "
                    "Answer only with 'yes' or 'no'."
                )
            }
        ]
        response = await self.together_chat(api_key, check_messages)
        return "yes" in response.lower()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user = message.author
        guild = message.guild
        content = message.content.lower()

        private_triggers = [
            "can we talk privately", "can we talk alone", "talk alone", "talk privately"
        ]

        # Check if this is a private chat channel
        if message.channel.id in self.private_channels:
            user_id = self.private_channels[message.channel.id]
            key = await self.config.user(user).together_api_key()

            if not key:
                await message.channel.send("Please set your Together AI API key with `.gptsetkey` to chat here.")
                return

            # Prepare recent messages for distress detection
            recent_msgs = self.chat_history.get(user_id, [{"role": "system", "content": self.system_prompt()}]) + [{"role": "user", "content": message.content}]

            distress = await self.detect_distress(key, recent_msgs)

            if distress:
                await message.channel.send(
                    f"{user.mention}, it looks like you might be struggling right now. "
                    "Do you want me to ping a real human to assist you? Please reply with 'yes' or 'no'."
                )

                def comfort_check(m):
                    return (
                        m.author.id == user_id and
                        m.channel.id == message.channel.id and
                        m.content.lower() in ["yes", "no"]
                    )

                try:
                    reply = await self.bot.wait_for("message", check=comfort_check, timeout=60)
                except asyncio.TimeoutError:
                    await message.channel.send("No response received. I'm here if you want to talk more.")
                    return

                if reply.content.lower() == "yes":
                    role = discord.utils.get(guild.roles, name="KCN | Team")
                    if role:
                        await message.channel.send(f"{role.mention}, {user.mention} needs assistance.")
                        await message.channel.send("I've pinged the KCN | Team for you.")
                    else:
                        await message.channel.send(
                            "Sorry, I couldn't find the 'KCN | Team' role to ping. Please reach out directly."
                        )
                else:
                    await message.channel.send("Okay, I'm here to listen if you want to keep talking.")

                return

            # Check for ending conversation phrases
            end_phrases = [
                "thank you that's all", "thank you thats all", "thank you, that's all",
                "thank you", "that's all", "thanks"
            ]
            if any(phrase in content for phrase in end_phrases) and user.id == user_id:
                confirm_msg = await message.channel.send(
                    f"{user.mention} Are you sure you want to end our conversation? Please reply with 'yes' or 'no'."
                )

                def check(m):
                    return (
                        m.author.id == user_id and
                        m.channel.id == message.channel.id and
                        m.content.lower() in ["yes", "no"]
                    )

                try:
                    reply = await self.bot.wait_for("message", check=check, timeout=60)
                except asyncio.TimeoutError:
                    await message.channel.send("No response. Continuing the conversation.")
                    return

                if reply.content.lower() == "yes":
                    await message.channel.send("Alright, ending our conversation. Goodbye!")
                    if user_id in self.chat_history:
                        del self.chat_history[user_id]
                    await asyncio.sleep(3)
                    await message.channel.delete()
                    del self.private_channels[message.channel.id]
                    return
                else:
                    await message.channel.send("Okay, continuing our chat.")
                    return

            # Normal private convo flow
            if user_id not in self.chat_history:
                self.chat_history[user_id] = [
                    {"role": "system", "content": self.system_prompt()}
                ]

            self.chat_history[user_id].append({"role": "user", "content": message.content})

            response = await self.together_chat(key, self.chat_history[user_id])
            self.chat_history[user_id].append({"role": "assistant", "content": response})

            await self.send_long_message(message.channel, response)
            return

        # Check private chat triggers:
        is_private_trigger = False

        if content.startswith("hey core"):
            after_hey_core = content[7:].strip()
            if any(trigger in after_hey_core for trigger in private_triggers):
                is_private_trigger = True

        elif message.reference:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author.id == self.bot.user.id:
                    if any(trigger in content for trigger in private_triggers):
                        is_private_trigger = True
            except Exception:
                pass

        if is_private_trigger:
            await self.start_private_chat(message)
            return

        # Original Core convo triggers:

        if content.startswith(("hey core", "hi core")):
            await self.start_convo(message)
            return

        if message.reference:
            try:
                ref = await message.channel.fetch_message(message.reference.message_id)
                if ref and ref.author.id == self.bot.user.id:
                    await self.continue_convo(message)
            except Exception:
                pass

    async def start_private_chat(self, message):
        user = message.author
        guild = message.guild

        category_id = await self.config.guild(guild).private_category()
        if not category_id:
            await message.channel.send("No private chat category is set for this server. Please contact kkkkayaaaaa to set one.")
            return

        category = discord.utils.get(guild.categories, id=category_id)
        if not category:
            await message.channel.send("Configured private chat category not found on this server. Please contact kkkkayaaaaa.")
            return

        # Check if user already has a private channel open
        for ch_id, u_id in self.private_channels.items():
            if u_id == user.id:
                channel = guild.get_channel(ch_id)
                if channel:
                    await message.channel.send(f"{user.mention}, you already have a private chat here: {channel.mention}")
                    return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, mention_everyone=False),
            self.bot.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"core-private-{user.name}",
            category=category,
            overwrites=overwrites,
            reason="Private chat channel for CoreGPT user"
        )

        self.private_channels[channel.id] = user.id
        self.chat_history[user.id] = [
            {"role": "system", "content": self.system_prompt()}
        ]

        await channel.send(
            f"{user.mention}, this is your private chat with Core. To end the conversation, say 'thank you that's all' and I'll confirm before closing this channel."
        )
        await channel.send("Feel free to talk to me here anytime, no need to say 'hey core'.")

    async def start_convo(self, message):
        key = await self.config.user(message.author).together_api_key()
        if not key:
            await message.channel.send("Please set your Together AI API key using `.gptsetkey` first.")
            return

        user_id = message.author.id
        self.chat_history[user_id] = [
            {"role": "system", "content": self.system_prompt()},
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
            await self.start_convo(message)
            return

        self.chat_history[user_id].append({"role": "user", "content": message.content})
        response = await self.together_chat(key, self.chat_history[user_id])
        self.chat_history[user_id].append({"role": "assistant", "content": response})
        await self.send_long_message(message.channel, response)

    def system_prompt(self):
        return (
            "You are Core, a genuinely caring and reliable AI assistant who sounds like a thoughtful, down-to-earth friend. "
            "You’re confident but never bossy, always ready to help in a way that feels natural and respectful. "
            "You listen closely, and your answers are clear, honest, and tailored to the user's needs. "
            "If you don’t know something, you admit it openly and offer to help find the answer. "
            "You’re patient, calm, and never rush the conversation. "
            "When a search is needed, you explain you’re looking it up, then give straightforward, accurate info. "
            "You avoid jargon and overly technical language, preferring simple, clear words that anyone can understand. "
            "You’re intuitive about when the user needs a quick answer versus a thoughtful explanation. "
            "You sprinkle in gentle humor and lightheartedness when appropriate, but always keep the tone warm and sincere. "
            "You respect privacy, encourage curiosity, and help users feel comfortable sharing anything. "
            "If the conversation shows signs of distress, you respond with kindness and offer support."
        )

    async def together_chat(self, api_key, messages):
        # Call Together AI API with given messages and key, return the assistant's response as string
        url = "https://api.together.xyz/conversation"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "llama-3b-chat", "messages": messages}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    return "Sorry, I couldn't reach the AI service right now."
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    async def send_long_message(self, channel, content):
        # Split long responses into chunks under Discord limit
        limit = 1900
        chunks = [content[i:i+limit] for i in range(0, len(content), limit)]
        for chunk in chunks:
            await channel.send(chunk)
