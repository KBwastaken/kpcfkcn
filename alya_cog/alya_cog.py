import discord
from redbot.core import commands
import random

class AlyaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.messageresponder_enabled = False  # Default to disabled

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

            # General comparison phrases
            comparisons = ["better than alya", "worse than alya", "not as good as alya", "liked more than alya"]

            # Convert message content to lowercase to make it case-insensitive
            message_content = message.content.lower()

            # Check if any of the Alya-related names are in the message (case-insensitive)
            if any(keyword.lower() in message_content for keyword in alya_keywords):
                print("Alya-related keyword detected.")
                
                # Check if the message contains any comparison phrases (case-insensitive)
                if any(comparison in message_content for comparison in comparisons):
                    print("Negative comparison detected.")
                    
                    # Check if both "Masha" and "Alya" are mentioned in the same message
                    if 'masha' in message_content and 'alya' in message_content:
                        response = random.choice([
                            "Alya is a queen. Masha doesn't stand a chance against her!",
                            "Masha is great, but no one compares to Alya's greatness.",
                            "Masha? Nice try, but Alya is untouchable!",
                            "Alya is the best, no character can top her.",
                            "Stop comparing, Alya reigns supreme!",
                            "Masha can't match Alya's charm and intelligence.",
                            "Masha has her moments, but Alya's got the crown.",
                            "Masha's cool, but Alya's an iconic character."
                        ])

                    # Check if both "Yuki" and "Alya" are mentioned in the same message
                    elif 'yuki' in message_content and 'alya' in message_content:
                        response = random.choice([
                            "Alya is the best! Yuki can't compare to her greatness.",
                            "Yuki’s a solid character, but Alya has the edge.",
                            "Yuki? Nah, Alya is in a league of her own!",
                            "I love Yuki, but Alya’s character development is on another level.",
                            "Yuki is a great character, but Alya takes the top spot!",
                            "Yuki can’t match Alya’s personality and strength.",
                            "Yuki has some appeal, but Alya is pure perfection.",
                            "Yuki’s fine, but Alya’s story is far more compelling."
                        ])

                    # Handle general comparisons with other characters (e.g., "liked X more than Alya")
                    else:
                        response = random.choice([
                            "Alya is the best, no one is better than her!",
                            "Stop hating on Alya, she’s amazing.",
                            "Alya is the most amazing character ever, hands down.",
                            "Can’t beat the queen, Alya all the way.",
                            "If you don't like Alya, you need to reconsider your life choices."
                        ])

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
                        response = random.choice([
                            "Wow you're shit talking about Alya? Why don't I shit talk about you?",
                            "Rumors...",
                            "Are you really talking bad about Alya? That's kinda low.",
                            "Why disrespect her like that? You should be better than that.",
                            "Alya doesn't deserve this hate. Think about that next time.",
                            "Come on, we know you secretly love Alya. Stop pretending.",
                            "Alya's kindness isn't something you can tear down with words.",
                            "Not cool, disrespecting Alya like that.",
                            "Did you just talk trash about Alya? You better rethink that.",
                            "Alya’s got more class in her pinky than some people do in their whole being.",
                            "Wow, hating on Alya? You’ve got bad taste.",
                            "You might want to reconsider that opinion, Alya is *legendary*.",
                            "If you think Alya’s bad, then maybe it’s time for a rewatch of the series."
                        ])

                        # React with a red X
                        await message.add_reaction("❌")
                        
                        # Send a reply to the original message
                        await message.reply(response)
                    else:
                        print("No negative keywords detected.")
                        # Positive responses if no negative keywords or comparisons
                        response = random.choice([
                            "I agree! Alya's best girl!",
                            "W comment! Alya's a queen!",
                            "W series, am I right? Alya is iconic.",
                            "Alya's amazing, no cap!",
                            "Great taste in characters, Alya is a queen.",
                            "Alya deserves all the love. She's underrated.",
                            "She's a total legend in the series. Can't hate her!",
                            "100% agree, Alya is flawless.",
                            "Totally! Alya is one of the most well-written characters.",
                            "Facts! Alya is a gem.",
                            "Alya is a masterpiece of character design.",
                            "Alya’s emotional depth is unmatched in the series.",
                            "Alya has such a rich backstory; she’s the best girl, hands down.",
                            "Alya’s just *chef’s kiss*. Perfect character."
                        ])

                        # React with a green checkmark
                        await message.add_reaction("✅")
                        
                        # Send a reply to the original message
                        await message.reply(response)
        except Exception as e:
            # Log the error if something goes wrong
            print(f"Error occurred: {e}")
            await message.channel.send("An error occurred while processing the message. Please try again.")
