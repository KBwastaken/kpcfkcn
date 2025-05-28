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
            "alert_role": None,
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
    async def setalertrole(self, ctx, role_id: str, state: bool):
        """Set or unset the alert role to be pinged"""
        try:
            role_id = int(role_id.strip("<@&>"))
        except ValueError:
            return await ctx.send("Invalid role ID or mention.")

        role = ctx.guild.get_role(role_id)
        if not role:
            return await ctx.send("Role not found in this server.")

        if state:
            await self.config.guild(ctx.guild).alert_role.set(role.id)
            await self.config.guild(ctx.guild).use_alert_role.set(True)
            await ctx.send(f"Alert role set to {role.mention}")
        else:
            await self.config.guild(ctx.guild).alert_role.set(None)
            await self.config.guild(ctx.guild).use_alert_role.set(False)
            await ctx.send("Alert role disabled.")

    @raid.command()
    async def confirm(self, ctx):
        """Trigger the raid alert if authorised"""
        guild = ctx.guild
        member = ctx.author

        alert_channel_id = await self.config.guild(guild).alert_channel()
        alert_role_id = await self.config.guild(guild).alert_role()
        use_alert_role = await self.config.guild(guild).use_alert_role()
        authorised_roles = await self.config.guild(guild).authorised_roles()

        if not any(role.id in authorised_roles for role in member.roles):
            return await ctx.send("You are not authorised to run this command.")

        alert_channel = guild.get_channel(alert_channel_id)
        if alert_channel is None:
            return await ctx.send("Alert channel not set or invalid.")

        # Get role mention and allow only that role to be pinged
        role = guild.get_role(alert_role_id) if alert_role_id and use_alert_role else None
        role_mention = role.mention if role else ""
        allowed_mentions = discord.AllowedMentions(roles=[role]) if role else discord.AllowedMentions.none()

        # Initial alert message
        confirm_text = (
            f"{role_mention} YOUR BASE IS BEING RAIDED\n"
            f"calling Kaya...\n"
            f"-# Action confirmed by {ctx.author.name}\n"
        )
        await alert_channel.send(content=confirm_text, allowed_mentions=allowed_mentions)

        # Repeating pings
        for _ in range(4):
            msg = await alert_channel.send(content=role_mention, allowed_mentions=allowed_mentions)
            await asyncio.sleep(1)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            await asyncio.sleep(1)


