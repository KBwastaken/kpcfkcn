import discord
from redbot.core import commands, app_commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list

class RestoreRoles(commands.Cog):
    """Restore or strip roles from users who leave and rejoin."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=545212345455, force_registration=True)

        default_guild = {"saved_roles": {}}
        self.config.register_guild(**default_guild)

        # Only these users can manage people with higher/equal roles
        self.whitelist = [
            1174820638997872721,  # replace with real IDs
        ]

    def is_manageable(self, acting: discord.Member, target: discord.Member) -> bool:
        return acting.top_role > target.top_role

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        roles = [role.id for role in member.roles if not role.is_default()]
        if roles:
            async with self.config.guild(member.guild).saved_roles() as saved:
                saved[str(member.id)] = roles

    @app_commands.command(name="restoreroles")
    async def restoreroles(self, interaction: discord.Interaction, user: discord.User):
        """Restore previously saved roles to a user."""

        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You need **Manage Roles** to use this.", ephemeral=True)
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I need **Manage Roles** to do that.", ephemeral=True)
            return

        member = interaction.guild.get_member(user.id)
        if not member:
            await interaction.response.send_message("That user is not in the server.", ephemeral=True)
            return

        if user.id not in self.whitelist and not self.is_manageable(interaction.user, member):
            await interaction.response.send_message(
                "You can't manage someone with a higher or equal role than you.", ephemeral=True
            )
            return

        if not self.is_manageable(interaction.guild.me, member):
            await interaction.response.send_message(
                "I can't manage that user. Their role is too high for me.", ephemeral=True
            )
            return

        saved = await self.config.guild(interaction.guild).saved_roles()
        role_ids = saved.get(str(user.id))
        if not role_ids:
            await interaction.response.send_message("No saved roles found for this user.", ephemeral=True)
            return

        roles = [interaction.guild.get_role(rid) for rid in role_ids if interaction.guild.get_role(rid)]
        try:
            await member.edit(roles=roles)
            await interaction.response.send_message(
                f"Restored roles to {member.mention}: {humanize_list([r.name for r in roles])}"
            )
        except discord.Forbidden:
            await interaction.response.send_message("I couldn't assign some roles due to permissions.", ephemeral=True)

    @app_commands.command(name="rolestrip")
    async def rolestrip(self, interaction: discord.Interaction, user: discord.User):
        """Strip all roles from a user (with confirmation)."""

        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You need **Manage Roles** to use this.", ephemeral=True)
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I need **Manage Roles** to do that.", ephemeral=True)
            return

        member = interaction.guild.get_member(user.id)
        if not member:
            await interaction.response.send_message("That user is not in the server.", ephemeral=True)
            return

        if user.id not in self.whitelist and not self.is_manageable(interaction.user, member):
            await interaction.response.send_message(
                "You can't manage someone with a higher or equal role than you.", ephemeral=True
            )
            return

        if not self.is_manageable(interaction.guild.me, member):
            await interaction.response.send_message(
                "I can't manage that user. Their role is too high for me.", ephemeral=True
            )
            return

        confirm_view = ConfirmView()
        await interaction.response.send_message(
            f"Are you **sure** you want to strip all roles from {member.mention}?",
            view=confirm_view,
            ephemeral=True
        )
        await confirm_view.wait()

        if not confirm_view.value:
            await interaction.followup.send("Role strip cancelled.", ephemeral=True)
            return

        roles = [r for r in member.roles if not r.is_default()]
        await self.config.guild(interaction.guild).saved_roles.set_raw(str(user.id), value=[r.id for r in roles])

        try:
            await member.edit(roles=[])
            await interaction.followup.send(f"Stripped all roles from {member.mention}.")
        except discord.Forbidden:
            await interaction.followup.send("Couldn't strip roles. I'm missing permissions.", ephemeral=True)

    @app_commands.command(name="unrolestrip")
    async def unrolestrip(self, interaction: discord.Interaction, user: discord.User):
        """Restore stripped roles to a user (with confirmation)."""

        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You need **Manage Roles** to use this.", ephemeral=True)
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I need **Manage Roles** to do that.", ephemeral=True)
            return

        member = interaction.guild.get_member(user.id)
        if not member:
            await interaction.response.send_message("That user is not in the server.", ephemeral=True)
            return

        if user.id not in self.whitelist and not self.is_manageable(interaction.user, member):
            await interaction.response.send_message(
                "You can't manage someone with a higher or equal role than you.", ephemeral=True
            )
            return

        if not self.is_manageable(interaction.guild.me, member):
            await interaction.response.send_message(
                "I can't manage that user. Their role is too high for me.", ephemeral=True
            )
            return

        saved = await self.config.guild(interaction.guild).saved_roles()
        role_ids = saved.get(str(user.id))
        if not role_ids:
            await interaction.response.send_message("No stripped roles saved for this user.", ephemeral=True)
            return

        confirm_view = ConfirmView()
        await interaction.response.send_message(
            f"Are you sure you want to restore roles to {member.mention}?",
            view=confirm_view,
            ephemeral=True
        )
        await confirm_view.wait()

        if not confirm_view.value:
            await interaction.followup.send("Unstrip cancelled.", ephemeral=True)
            return

        roles = [interaction.guild.get_role(rid) for rid in role_ids if interaction.guild.get_role(rid)]
        try:
            await member.edit(roles=roles)
            await interaction.followup.send(f"Restored roles to {member.mention}.")
        except discord.Forbidden:
            await interaction.followup.send("Couldn't assign some roles due to permissions.", ephemeral=True)

class ConfirmView(discord.ui.View):
    def __init__(self, timeout=30):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()
