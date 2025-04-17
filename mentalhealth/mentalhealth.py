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
        self.config.register_guild(request_channel=None)

        self.alert_guild_id = 1256345356199788667
        self.alert_channel_id = 1340519019760979988
        self.support_role_id = 1356688519317422322

    @app_commands.command(name="mhset", description="Set the request channel.")
    @app_commands.guild_only()
    async def mhset(self, interaction: discord.Interaction, request_channel: discord.TextChannel):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Run this in a server.", ephemeral=True)
            return

        await self.config.guild(guild).request_channel.set(request_channel.id)

        await interaction.response.send_message(f"✅ Configured for {request_channel.mention}", ephemeral=True)

    @redcommands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        request_channel_id = await self.config.guild(message.guild).request_channel()
        if message.channel.id != request_channel_id:
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
            embed.set_footer(text=f"Requested by {message.author.name}", icon_url=message.author.display_avatar.url)
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

        # Hardcoded role ping (we no longer get it from the command)
        role_ping_text = f"<@&{self.support_role_id}>" if wants_help else ""

        if wants_help:
            embed.add_field(name="Status", value=f"{self.user_message.author.name} asked for help. {role_ping_text}", inline=False)
        else:
            embed.add_field(name="NOTICE", value="⚠️ THIS USER DID NOT ASK FOR HELP. DO NOT DM.", inline=False)

        embed.set_footer(text=f"Requested by {self.user_message.author.name}", icon_url=self.user_message.author.display_avatar.url)

        await channel.send(content=role_ping_text if wants_help else "", embed=embed)
        self.stop()
