import discord
from redbot.core import commands
from redbot.core.bot import Red

ALLOWED_GLOBAL_IDS = {1174820638997872721, 1274438209715044415, 690239097150767153}
APPEAL_LINK = "https://forms.gle/gR6f9iaaprASRgyP9"

class ServerBan(commands.Cog):
    """Force-ban or unban users by ID with global option and appeal messaging."""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command(name="sban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sban(self, ctx: commands.Context, user_id: int, global_flag: str, *, reason: str = None):
        """Ban a user by ID with optional global effect and DM appeal info."""
        moderator = ctx.author
        is_global = global_flag.lower() == "yes"

        if is_global and moderator.id not in ALLOWED_GLOBAL_IDS:
            await ctx.send("You are not authorized to use global bans.")
            return

        target_guilds = self.bot.guilds if is_global else [ctx.guild]

        if not reason:
            reason = f"Action requested by {moderator.name} ({moderator.id})"

        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(
                title="You have been banned",
                description=f"**Reason:** {reason}\n\n"
                            f"**Servers:** {'globalban' if is_global and len(target_guilds) > 1 else ctx.guild.name}\n\n"
                            "You may appeal using the link below. Appeals will be reviewed within 12 hours.\n"
                            "Try rejoining after 24 hours. If still banned, you can reapply in 30 days.",
                color=discord.Color.red()
            )
            embed.add_field(name="Appeal Link", value=f"[Click here to appeal]({APPEAL_LINK})", inline=False)
            embed.set_footer(text="Appeals are reviewed by the moderation team.")
            await user.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("Could not DM the user, but proceeding with the ban.")

        for guild in target_guilds:
            try:
                is_banned = False
                async for entry in guild.bans():
                    if entry.user.id == user_id:
                        is_banned = True
                        break
                if is_banned:
                    await ctx.send(f"User is already banned in {guild.name}.")
                    continue

                await guild.ban(discord.Object(id=user_id), reason=reason)
                await ctx.send(f"Banned `{user_id}` in {guild.name}.")
            except Exception as e:
                await ctx.send(f"Failed to ban in {guild.name}: {e}")

    @commands.command(name="sunban")
    @commands.guild_only()
    @commands.admin_or_permissions(ban_members=True)
    async def sunban(self, ctx: commands.Context, user_id: int, *, reason: str = "Your application has been accepted, you can now rejoin the server using the previous link or by requesting it with the button below"):
        """Unban a user and send them an invite link, trying to use past DMs first."""
        guild = ctx.guild
        invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)

        try:
            # Try to unban the user directly without iterating through the bans list
            await guild.unban(discord.Object(id=user_id), reason=reason)

            # If no error occurred, proceed to send DM to the user
            try:
                user = await self.bot.fetch_user(user_id)
                channel = user.dm_channel or await user.create_dm()

                embed = discord.Embed(
                    title="You have been unbanned",
                    description=f"**Reason:** {reason}\n\n"
                                f"**Server:** {guild.name}\n\n"
                                "Click the button below to rejoin the server.",
                    color=discord.Color.green()
                )
                view = discord.ui.View()
                button = discord.ui.Button(label="Rejoin Server", url=invite.url, style=discord.ButtonStyle.link)
                view.add_item(button)

                await channel.send(embed=embed, view=view)
            except discord.NotFound:
                await ctx.send("User not found. They may have deleted their account.")
            except discord.Forbidden:
                await ctx.send("Could not DM the user.")

            await ctx.send(f"User with ID `{user_id}` has been unbanned from {guild.name}.")

        except discord.NotFound:
            await ctx.send("The user is not banned.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to unban this user.")
        except Exception as e:
            await ctx.send(f"An error occurred while unbanning: {e}")

async def setup(bot: Red):
    await bot.add_cog(ServerBan(bot))
