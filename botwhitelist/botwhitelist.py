import json
import logging
from redbot.core import commands
import discord

# Set up logging globally to prevent double logging
logger = logging.getLogger("botwhitelist")
if not logger.hasHandlers():  # Ensure we only set up handlers once
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class BotWhitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist = self.load_whitelist()  # Load the whitelist from the file
        logger.info(f"BotWhitelist cog initialized. Current whitelist: {self.whitelist}")

    def load_whitelist(self):
        """Load the whitelist from a file"""
        try:
            with open('whitelist.json', 'r') as file:
                whitelist = set(json.load(file))
                logger.info(f"Whitelist loaded from file: {whitelist}")
                return whitelist
        except FileNotFoundError:
            logger.warning("Whitelist file not found, initializing empty whitelist.")
            return set()  # If file doesn't exist, return an empty set

    def save_whitelist(self):
        """Save the whitelist to a file"""
        with open('whitelist.json', 'w') as file:
            json.dump(list(self.whitelist), file)
            logger.info(f"Whitelist saved to file: {self.whitelist}")

    @commands.command()
    @commands.is_owner()  # Ensures that only the bot owner can use this command
    async def whitelistbot(self, ctx, bot_id: int):
        """Add or remove a bot to/from the whitelist"""
        logger.info(f"Attempting to add/remove bot with ID {bot_id} to/from the whitelist.")
        
        if bot_id in self.whitelist:
            self.whitelist.remove(bot_id)
            await ctx.send(f"Bot with ID {bot_id} has been removed from the whitelist.")
            logger.info(f"Bot with ID {bot_id} removed from the whitelist.")
        else:
            self.whitelist.add(bot_id)
            await ctx.send(f"Bot with ID {bot_id} has been added to the whitelist.")
            logger.info(f"Bot with ID {bot_id} added to the whitelist.")
        
        # Save the updated whitelist to the file
        self.save_whitelist()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Automatically kicks unwhitelisted bots upon joining"""
        if member.bot:  # Check if the member is a bot
            logger.info(f"Bot {member.name} ({member.id}) joined the server. Current whitelist: {self.whitelist}")
            if member.id not in self.whitelist:
                # If the bot is not in the whitelist, kick it
                try:
                    await member.kick(reason="Bot not whitelisted.")
                    logger.info(f"Bot {member.name} ({member.id}) kicked because it is not whitelisted.")
                    
                    # Send an asynchronous message to the system channel if it exists
                    if member.guild.system_channel:
                        await member.guild.system_channel.send(f"A bot ({member.name}) has been kicked because it is not on the whitelist.")
                except Exception as e:
                    logger.error(f"Error kicking bot {member.name} ({member.id}): {e}")
            else:
                # Log the joining of a whitelisted bot
                logger.info(f"Whitelisted bot {member.name} ({member.id}) allowed to join the server.")

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(BotWhitelist(bot))  # Await add_cog to avoid the warning/error
    logger.info("BotWhitelist cog has been added to the bot.")
