import discord
from redbot.core import commands
import random

class AlyaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.messageresponder_enabled = False  # Default to disabled

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.messageresponder_enabled:
            return  # If the responder is disabled, do nothing

        # Ignore messages sent by the bot itself
        if message.author == self.bot.user:
            return

        # List of possible Alya-related phrases
        alya_keywords = [
            "Alya", "Alisa", "Alisa Mikhailovna", "Alisa Mikhailovna Kujou", 
            "Mikhailovna Kujou", "Alya Mikhailovna Kujou", "Alya Mikhailovna", 
            "Alya sometimes", "Alya Sometimes Hides Her Feelings in Russian"
        ]
        
        # Negative phrases to check for
        negative_keywords = ["sucks", "is bad", "overrated", "worst", "hate", "terrible", "annoying"]
        
        # Check if any of the Alya-related names are in the message
        if any(keyword in message.content for keyword in alya_keywords):
            # Check if any negative keywords are in the message
            if any(negative_keyword in message.content.lower() for negative_keyword in negative_keywords):
                # Random choice for additional "shit talking" responses
                shit_talk_responses = [
                    "Wow you're shit talking about Alya? Why don't I shit talk about you?",
                    "Rumors...",
                    "Are you really talking bad about Alya? That's kinda low.",
                    "Why disrespect her like that? You should be better than that."
                ]
                response = random.choice(shit_talk_responses)

                # React with a red X
                await message.add_reaction("❌")
                
                # Send a reply
                await message.channel.send(response)
            else:
                # Positive responses if no negative keywords
                positive_responses = [
                    "I agree!",
                    "W comment!",
                    "W series, am I right?",
                    "Alya's amazing, no cap!",
                    "Great taste in characters, Alya is a queen."
                ]
                response = random.choice(positive_responses)

                # React with a green checkmark
                await message.add_reaction("✅")
                
                # Send a positive reply
                await message.channel.send(response)

    @commands.command()
    async def messageresponder(self, ctx, status: str):
        """Enable or disable the message responder."""
        if status.lower() in ['true', 'enable', 'on']:
            self.messageresponder_enabled = True
            await ctx.send("Message responder has been enabled.")
        elif status.lower() in ['false', 'disable', 'off']:
            self.messageresponder_enabled = False
            await ctx.send("Message responder has been disabled.")
        else:
            await ctx.send("Please use 'true'/'false', 'enable'/'disable', or 'on'/'off' to toggle the responder.")

