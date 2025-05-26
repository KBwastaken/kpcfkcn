import discord
from redbot.core import commands, Config
import asyncio

class Raid(commands.Cog):
    """Raid alert system"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {
            "authorised_roles": [],
            "alert_channel": None,
            "use_alert_role": False
        }
        self.config.register_guild(**default_guild)

    @commands.group()
    async def raid(self, ctx):
        """Raid base command"""
        pass

    @raid.command()
    async def setauthorised(self, ctx, role_id: int, state: bool):
        """Add/remove an authorised role"""
        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send("Invalid role ID.")
        async with self.config.guild(ctx.guild).authorised_roles() as roles:
            if state:
                if role_id not in roles:
                    roles.append(role_id)
                    await ctx.send(f"Role {role.name} added to authorised list.")
                else:
                    await ctx.send(f"Role {role.name} is already authorised.")
            else:
                if role_id in roles:
                    roles.remove(role_id)
                    await ctx.send(f"Role {role.name} removed from authorised list.")
                else:
                    await ctx.send(f"Role {role.name} is not in the authorised list.")

    @raid.command()
    async def setchannel(self, ctx, channel: discord.TextChannel, state: bool):
        """Set or unset the alert channel"""
        if state:
            await self.config.guild(ctx.guild).alert_channel.set(channel.id)
            await ctx.send(f"Alert channel set to {channel.mention}")
        else:
            await self.config.guild(ctx.guild).alert_channel.set(None)
            await ctx.send("Alert channel has been unset.")

    @raid.command()
    async def setalertrole(self, ctx, state: bool):
        """Enable or disable alert role pings"""
        await self.config.guild(ctx.guild).use_alert_role.set(state)
        status = "enabled" if state else "disabled"
        await ctx.send(f"Alert role pings have been {status}.")

    @raid.command()
    async def confirm(self, ctx):
        """Trigger the raid alert if authorised"""
        guild = ctx.guild
        member = ctx.author

        alert_channel_id = await self.config.guild(guild).alert_channel()
        use_alert_role = await self.config.guild(guild).use_alert_role()
        authorised_roles = await self.config.guild(guild).authorised_roles()

        # Check authorisation
        if not any(role.id in authorised_roles for role in member.roles):
            return await ctx.send("You are not authorised to run this command.")

        # Resolve alert channel
        alert_channel = guild.get_channel(alert_channel_id)
        if alert_channel is None:
            return await ctx.send("Alert channel not set or invalid.")

        alert_mention = "@here" if use_alert_role else ""
        confirm_text = (
            f"{alert_mention} YOUR BASE IS BEING RAIDED\n"
            f"= # Action confirmed by {ctx.author.name}"
        )
        await alert_channel.send(confirm_text)

        # Send alert messages
        for _ in range(4):
            msg = await alert_channel.send(alert_mention)
            await asyncio.sleep(1)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            await asyncio.sleep(1)

