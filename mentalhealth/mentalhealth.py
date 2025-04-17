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

    @app_commands.command(name="mhset", description="Set or unset the mental health request channel.")
    @app_commands.guild_only()
    async def mhset(self, interaction: discord.Interaction, request_channel: discord.TextChannel):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Run this in a server.", ephemeral=True)
            return

        current = await self.config.guild(guild).request_channel()

        if current == request_channel.id:
            await self.config.guild(guild).request_channel.set(None)
            await interaction.response.send_message(f"❌ Channel {request_channel.mention} has been removed as the request channel.", ephemeral=True)
        else:
            await self.config.guild(guild).request_channel.set(request_channel.id)
            await interaction.response.send_message(f"✅ {request_channel.mention} set as the request channel.", ephemeral=True)

    @redcommands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        request_channel_id = await self.config.guild(message.guild).request_channel()
        if message.channel.id != request_channel_id:
            return

        try:
            embed = discord.Embed(
                title="You're not alone 💙",
                description=(
                    "We just wanted to check in on you — it looks like you might be going through something right now.\n\n"
                    "**Please know this:** You matter. Your feelings are valid. Asking for help is a sign of strength, not weakness. 💪\n\n"
                    "If you'd like someone from our trusted support team to reach out, just click the button below.\n"
                    "We'll handle everything with care, respect, and complete confidentiality.\n\n"
                    "*You're never alone — we're here when you're ready.* ❤️"
                ),
                color=discord.Color.blurple()
            )
            embed.set_footer(text="Your mental health matters")
            view = ButtonView(self.bot, message, self.support_role_id)
            await message.author.send(embed=embed, view=view)
        except discord.Forbidden:
            pass

    @app_commands.command(name="mhsend", description="Send a mental health awareness message.")
    @app_commands.guild_only()
    async def mhsend(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Mental Health",
            description=(
                "**Mental health** is an important aspect of our overall well-being, yet it's often overlooked or **misunderstood**. "
                "The reality is that mental health struggles can be incredibly **isolating**, and many people **suffer** in silence. "
                "Tragically, the statistics show the severity of this issue, every **11** minutes, someone dies by **su1c!de**. "
                "That’s one **life** lost every **11 minutes** to a problem that, with the right **support**, could be addressed. "
                "These numbers are a stark reminder that **mental health** isn’t something to take **lightly**, and it’s essential "
                "that we break the silence around it. Talking about our **feelings**, seeking **support**, and opening up to others can make all the **difference**. "
                "It’s important to remember that reaching out for help doesn’t show **weakness**, it shows strength. No matter what you're going through, whether it's "
                "**anxiety**, **depression**, or any other **mental health** challenge, it's okay to ask for **help**. We all have struggles, and **it’s okay** to lean "
                "on others for support. If you feel **alone** or **overwhelmed**, talking to someone can be the first step toward **healing**. "
                "You don’t have to carry your burdens **alone**. We all **deserve** support, compassion, and a chance to **heal**, and it's okay to ask for it when we need it.\n\n"
                "__**You matter, and your mental health matters.**__\n\n"
                f"Send a message in {channel.mention}. The team is professional and will NEVER share anything."
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Sent in {interaction.guild.name}")
        await channel.send(embed=embed)

    class ButtonView(discord.ui.View):
        def __init__(self, bot, user_message: discord.Message, support_role_id: int):
            super().__init__(timeout=300)
            self.bot = bot
            self.user_message = user_message
            self.support_role_id = support_role_id

        @discord.ui.button(label="Ask for help!", style=discord.ButtonStyle.success)
        async def ask_help(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.process(interaction, wants_help=True)

        @discord.ui.button(label="I'm not ready yet", style=discord.ButtonStyle.secondary)
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

            if wants_help:
                embed.add_field(
                    name="Status",
                    value=f"{self.user_message.author.mention} asked for help.",
                    inline=False
                )
                role_ping_text = f"<@&{self.support_role_id}>"
            else:
                embed.add_field(
                    name="NOTICE",
                    value="⚠️ THIS USER DID NOT ASK FOR HELP. DO NOT DM.",
                    inline=False
                )
                role_ping_text = ""

            embed.set_footer(text=f"Requested by {self.user_message.author.name} | Sent in {self.user_message.guild.name}",
                             icon_url=self.user_message.author.display_avatar.url)

            # Replacing the send method with the allowed_mentions argument
            allowed_mentions = discord.AllowedMentions(roles=True)
            await channel.send(content=role_ping_text, embed=embed, allowed_mentions=allowed_mentions)
            self.stop()


async def setup(bot: Red):
    await bot.add_cog(MentalHealth(bot))
