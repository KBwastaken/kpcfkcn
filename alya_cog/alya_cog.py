import discord
from redbot.core import commands
import random

class AlyaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.messageresponder_enabled = False  # Default to disabled

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if not self.messageresponder_enabled:
                return  # If the responder is disabled, do nothing

            # Ignore messages sent by the bot itself
            if message.author == self.bot.user:
                return

            # Debug: Print the message content to the logs
            print(f"Message received: {message.content}")

            # List of possible Alya-related phrases
            alya_keywords = [
                "Alya", "Alisa", "Alisa Mikhailovna", "Alisa Mikhailovna Kujou", 
                "Mikhailovna Kujou", "Alya Mikhailovna Kujou", "Alya Mikhailovna", 
                "Alya sometimes", "Alya Sometimes Hides Her Feelings in Russian"
            ]
            
            # Negative phrases to check for
            negative_keywords = ["sucks", "is bad", "overrated", "worst", "hate", "terrible", "annoying"]

            # Specific character names for comparisons
            comparisons = ["better than alya", "worse than alya", "not as good as alya"]

            # Convert message content to lowercase to make it case-insensitive
            message_content = message.content.lower()

            # Check if any of the Alya-related names are in the message (case-insensitive)
            if any(keyword.lower() in message_content for keyword in alya_keywords):
                print("Alya-related keyword detected.")
                
                # Check if the message contains any comparison phrases (case-insensitive)
                if any(comparison in message_content for comparison in comparisons):
                    print("Negative comparison detected.")
                    
                    # Response if another character is being compared as better than Alya
                    negative_comparison_responses = [
                        "Alya is a queen. There's no comparison!",
                        "Comparing Alya to someone else? No one is as unique as her!",
                        "Alya is irreplaceable. No one can top her!",
                        "Nope, Alya is the best, you can't compare her to anyone.",
                        "No one can surpass Alya, she’s the ultimate best girl!"
                    ]
                    response = random.choice(negative_comparison_responses)

                    # React with a red X
                    await message.add_reaction("❌")
                    
                    # Send a reply to the original message
                    await message.reply(response)
                else:
                    print("No negative comparison detected.")
                    # Check if any negative keywords are in the message (case-insensitive)
                    if any(negative_keyword in message_content for negative_keyword in negative_keywords):
                        print("Negative keyword detected.")
                        # Random choice for additional "shit talking" responses
                        shit_talk_responses = [
                            "Wow you're shit talking about Alya? Why don't I shit talk about you?",
                            "Rumors...",
                            "Are you really talking bad about Alya? That's kinda low.",
                            "Why disrespect her like that? You should be better than that.",
                            "Alya doesn't deserve this hate. Think about that next time.",
                            "Come on, we know you secretly love Alya. Stop pretending.",
                            "Alya's kindness isn't something you can tear down with words."
                        ]
                        response = random.choice(shit_talk_responses)

                        # React with a red X
                        await message.add_reaction("❌")
                        
                        # Send a reply to the original message
                        await message.reply(response)
                    else:
                        print("No negative keywords detected.")
                        # Positive responses if no negative keywords or comparisons
                        positive_responses = [
                            "I agree! Alya's best girl!",
                            "W comment! Alya's a queen!",
                            "W series, am I right? Alya is iconic.",
                            "Alya's amazing, no cap!",
                            "Great taste in characters, Alya is a queen.",
                            "Alya deserves all the love. She's underrated.",
                            "She's a total legend in the series. Can't hate her!",
                            "100% agree, Alya is flawless.",
                            "Totally! Alya is one of the most well-written characters.",
                            "Facts! Alya is a gem."
                        ]
                        response = random.choice(positive_responses)

                        # React with a green checkmark
                        await message.add_reaction("✅")
                        
                        # Send a reply to the original message
                        await message.reply(response)
        except Exception as e:
            # Log the error if something goes wrong
            print(f"Error occurred: {e}")
            await message.channel.send("An error occurred while processing the message. Please try again.")

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
