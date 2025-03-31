import discord
from redbot.core import commands, Config, checks

class BlockJoins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=123456789)
        self.config.register_guild(blocking=False, reason="The server has been locked by {author} due to security reasons.", blocker_id=None)
    
    @commands.command()
    @checks.is_owner()
    async def blockjoins(self, ctx, *, reason: str = None):
        """Toggle blocking new users from joining the server."""
        guild = ctx.guild
        is_blocking = await self.config.guild(guild).blocking()
        
        if is_blocking:
            await self.config.guild(guild).blocking.set(False)
            await self.config.guild(guild).blocker_id.set(None)
            await ctx.send("🔓 New user joins are now **unblocked**.")
        else:
            reason = reason or f"The server has been locked by {ctx.author} due to security reasons."
            await self.config.guild(guild).blocking.set(True)
            await self.config.guild(guild).reason.set(reason)
            await self.config.guild(guild).blocker_id.set(ctx.author.id)
            await ctx.send("🔒 New user joins are now **blocked**.")
            
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        is_blocking = await self.config.guild(guild).blocking()
        reason = await self.config.guild(guild).reason()
        blocker_id = await self.config.guild(guild).blocker_id()
        blocker = guild.get_member(blocker_id) if blocker_id else None
        
        if is_blocking and blocker:
            try:
                class RespondButton(discord.ui.View):
                    def __init__(self, bot, blocker, member):
                        super().__init__()
                        self.bot = bot
                        self.blocker = blocker
                        self.member = member
                        self.sent = False

                    @discord.ui.button(label="Send Message Back", style=discord.ButtonStyle.primary)
                    async def send_message(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if self.sent:
                            return
                        
                        modal = discord.ui.Modal(title="Send a Message")
                        message_input = discord.ui.TextInput(
                            label="Your message:",
                            style=discord.TextStyle.long,
                            required=True
                        )
                        modal.add_item(message_input)

                        async def callback(interaction: discord.Interaction):
                            embed = discord.Embed(
                                title="Response from a new user",
                                description=f"**User:** {self.member.name}#{self.member.discriminator}\n"
                                            f"**User ID:** {self.member.id}\n"
                                            f"**Message:** {message_input.value}\n\n"
                                            f"This message was sent in response to the security lock.",
                                color=discord.Color.blue()
                            )
                            await self.blocker.send(embed=embed)
                            await interaction.response.send_message("Your message has been sent!", ephemeral=True)
                            button.disabled = True
                            self.sent = True
                            await interaction.message.edit(view=self)

                        modal.on_submit = callback
                        await interaction.response.send_modal(modal)

                dm_embed = discord.Embed(
                    title="Server Locked",
                    description=reason,
                    color=discord.Color.red()
                )
                view = RespondButton(self.bot, blocker, member)
                await member.send(embed=dm_embed, view=view)
            except discord.HTTPException:
                pass
            
            # Fetch and delete the invite the user used
            invites = await guild.invites()
            for invite in invites:
                if invite.uses > 0:
                    await invite.delete(reason="Auto-deleting used invite from blocked join.")
                    break
            
            await member.kick(reason="Server is locked. Auto-kicked new join.")
