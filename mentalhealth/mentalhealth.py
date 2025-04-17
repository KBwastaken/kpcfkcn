import discord
from discord.ext import commands
from discord import app_commands
from redbot.core import commands as redcommands, Config
from redbot.core.bot import Red
from typing import Optional


class MentalHealth(redcommands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_guild(request_channel=None, role_ping=None)

        # Hardcoded alert destination
        self.alert_guild_id = 1256345356199788667  # CHANGE THIS
        self.alert_channel_id = 1340519019760979988  # CHANGE THIS

    @redcommands.is_owner()
    @app_commands.command(name="mhset", description="Set request channel and optional ping role.")
    @app_commands.guild_only()
    async def mhset(
        self,
        interaction: discord.Interaction,
        request_channel: discord.TextChannel,
        role_ping: Optional[discord.Role] = None
    ):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Run this in a server.", ephemeral=True)
            return

        await self.config.guild(guild).request_channel.set(request_channel.id)
        await self.config.guild(guild).role_ping.set(role_ping.id if role_ping else None)

        msg = f"✅ Configured for {request_channel.mention}"
        if role_ping:
            msg += f" with {role_ping.mention}"
        await interaction.response.send_message(msg, ephemeral=True)

    @redcommands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        guild_conf = self.config.guild(message.guild)
        request_channel_id = await guild_conf.request_channel()
        if not request_channel_id or message.channel.id != request_channel_id:
            return

        try:
            embed = discord.Embed(
                title="Hey there 💙",
                description=(
                    "This message is automated and **not monitored** by humans.\n\n"
                    "We noticed you might be going through something, and that’s okay.\n"
                    "Click a button below to let us know if you'd like someone to reach out.\n\n"
                    "It’s **100% safe** and **confidential**."
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Nothing is logged, and the team will be notified in a different Discord server not including the server owner.")
            view = ButtonView(self.bot, message)
            await message.author.send(embed=embed, view=view)
        except discord.Forbidden:
            pass


class ButtonView(discord.ui.View):
    def __init__(self, bot, user_message: discord.Message):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_message = user_message

    @discord.ui.button(label="Ask for help!", style=discord.ButtonStyle.success)
    async def ask_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, wants_help=True)

    @discord.ui.button(label="I’m not ready yet", style=discord.ButtonStyle.secondary)
    async def not_ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, wants_help=False)

    async def process(self, interaction: discord.Interaction, wants_help: bool):
        await interaction.response.send_message("Thanks for letting us know 💙", ephemeral=True)
        embed = discord.Embed(
            title=self.user_message.author.name,
            description=self.user_message.content,
            color=discord.Color.green() if wants_help else discord.Color.orange()
        )
        embed.set_thumbnail(url=self.user_message.author.display_avatar.url)

        cog = self.bot.get_cog("MentalHealth")
        channel = cog.bot.get_guild(cog.alert_guild_id).get_channel(cog.alert_channel_id)

        role_id = await cog.config.guild(self.user_message.guild).role_ping()
        role_ping_text = f"<@&{role_id}>" if role_id and wants_help else ""

        if wants_help:
            embed.add_field(name="Status", value=f"{self.user_message.author.name} asked for help. {role_ping_text}", inline=False)
        else:
            embed.add_field(name="NOTICE", value="⚠️ THIS USER DID NOT ASK FOR HELP. DO NOT DM.", inline=False)

        await channel.send(content=role_ping_text if wants_help else "", embed=embed)
        self.stop()
