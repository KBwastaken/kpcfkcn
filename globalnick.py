import discord
from redbot.core import commands
from redbot.core.commands import Context
from typing import Optional

class GlobalNick(commands.Cog):
    """A cog for globally changing a user's nickname across all servers."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def globalnick(self, ctx: Context, user: Optional[discord.Member] = None, *, nickname: str = None):
        """Globally change a user's nickname across all servers the bot is in."""
        if user is None:
            user = ctx.author  # If no user is provided, use the command executor.

        if nickname is None:
            await ctx.send("Please provide a nickname.")
            return

        # Iterate through all the guilds the bot is in
        for guild in self.bot.guilds:
            # Ensure the bot has the necessary permissions and can fetch members
            try:
                # Fetch member data to ensure we get the most up-to-date member
                member = await guild.fetch_member(user.id)
                bot_member = guild.get_member(self.bot.user.id)

                if bot_member:
                    # Log bot's permissions to check if it can manage nicknames
                    bot_permissions = bot_member.guild_permissions
                    if bot_permissions.manage_nicknames:
                        try:
                            # Change the user's nickname globally
                            await member.edit(nick=nickname)
                            await ctx.send(f"Successfully changed the nickname of {user} to `{nickname}` in {guild.name}.")
                        except discord.Forbidden:
                            await ctx.send(f"Could not change nickname for {user} in {guild.name}, missing permissions.")
                        except discord.HTTPException as e:
                            await ctx.send(f"Failed to change nickname for {user} in {guild.name}: {e}")
                    else:
                        await ctx.send(f"Bot does not have 'Manage Nicknames' permission in {guild.name}.")
                else:
                    await ctx.send(f"Bot cannot find its own member data in {guild.name}. Please check if it is properly added to the server.")

            except discord.NotFound:
                await ctx.send(f"{user} is not a member of {guild.name}.")
            except discord.Forbidden:
                await ctx.send(f"Bot doesn't have permission to fetch member {user} in {guild.name}.")
            except discord.HTTPException as e:
                await ctx.send(f"Error occurred when fetching member {user} in {guild.name}: {e}")
            except Exception as e:
                await ctx.send(f"An unexpected error occurred in {guild.name}: {str(e)}")
                print(f"Error in guild {guild.name}: {e}")  # Print the error to the console for debugging

    @globalnick.error
    async def globalnick_error(self, ctx: Context, error: Exception):
        """Handles errors that occur during the .globalnick command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command. Only administrators can use it.")
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send("An error occurred while trying to change the nickname.")
        else:
            raise error
