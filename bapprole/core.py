from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from discord import Embed, Color, AllowedMentions, Interaction
from redbot.core.utils.menus import start_adding_reactions
from discord.ext import tasks
from discord import app_commands
from discord import Interaction
import discord
import asyncio

class bapprole(commands.Cog):
    """Manage bapp role across all servers"""

    owner_id = 1174820638997872721  # Your owner ID
    role_name = "KCN.gg"
    role_color = "#77bcd6"
    hoist = True

    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(bapp_users=[])
        self.config.register_global(admin_settings={})
        self.bot.loop.create_task(self.setup_slash_command())
        self.update_loop.start()
        bot_id = self.bot.user.id  # Get the bot's user ID

    @tasks.loop(seconds=7200)
    async def update_loop(self):
        await self.bot.wait_until_ready()
        bapp_users = await self.config.bapp_users()

        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=self.role_name)
                if not role:
                    continue

                current_members = {m.id for m in role.members}
                to_remove = current_members - set(bapp_users)
                to_add = set(bapp_users) - current_members

                for uid in to_remove:
                    member = guild.get_member(uid)
                    if member:
                        await member.remove_roles(role)

                for uid in to_add:
                    member = guild.get_member(uid)
                    if member:
                        await member.add_roles(role)

            except Exception:
                continue

    async def setup_slash_command(self):
        await self.bot.wait_until_ready()
        self.tree.add_command(self.request_admin)

    @commands.command()
    @commands.is_owner()
    async def setadminconfig(self, ctx, channel: discord.TextChannel, role: discord.Role):
        """Set the admin request channel and admin role mention."""
        await self.config.admin_settings.set({
            "channel_id": channel.id,
            "role_id": role.id
        })
        await ctx.send(f"Admin request channel set to {channel.mention} and role set to {role.name}.")


@app_commands.command(name="requestadmin", description="Request temporary KCN.gg admin access.")
@app_commands.describe(reason="Reason for your request")
async def request_admin(self, interaction: Interaction, reason: str):

    await interaction.response.defer(ephemeral=True)

    settings = await self.config.admin_settings()
    if not settings:
        await interaction.followup.send("Admin role request system not configured.", ephemeral=True)
        return

    review_channel = self.bot.get_channel(settings.get("channel_id"))
    if not review_channel:
        await interaction.followup.send("Configured review channel not found.", ephemeral=True)
        return

    # Get the target role in the *requesting* guild by name or ID, ensure it exists in requesting server
    role_id = settings.get("role_id")
    target_role = interaction.guild.get_role(role_id)
    if not target_role:
        await interaction.followup.send("Configured admin role not found in this server.", ephemeral=True)
        return

    embed = Embed(
        title="Admin Role Request",
        description=(
            f"**User:** {interaction.user.mention} ({interaction.user} / ID: {interaction.user.id})\n"
            f"**Server:** {interaction.guild.name} (ID: {interaction.guild.id})\n"
            f"**Reason:** {reason}"
        ),
        color=Color.orange()
    )

    # Ping the admin role on the review server to notify admins
    allowed_mentions = discord.AllowedMentions(roles=True)
    msg = await review_channel.send(content=target_role.mention, embed=embed, allowed_mentions=allowed_mentions)

    # Add approval reactions
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, user):
        return (
            user.guild_permissions.administrator and
            str(reaction.emoji) in ["✅", "❌"] and
            reaction.message.id == msg.id
        )

    try:
        reaction, user = await self.bot.wait_for("reaction_add", timeout=300.0, check=check)

        if str(reaction.emoji) == "✅":
            await interaction.user.add_roles(target_role, reason=f"Approved admin access by {user} for 30 minutes")
            await interaction.followup.send("Request approved. Role granted for 30 minutes.", ephemeral=True)

            # Wait 30 minutes, then remove role with reason
            await asyncio.sleep(10)
            await interaction.user.remove_roles(target_role, reason="Timed admin access expired")
        else:
            await interaction.followup.send("Request denied.", ephemeral=True)

    except asyncio.TimeoutError:
        await interaction.followup.send("No response from admins. Request timed out.", ephemeral=True)



    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete"""
        pass

    async def bot_owner_check(self, ctx):
        """Check if user is the defined owner"""
        return ctx.author.id == self.owner_id

    async def bapp_member_check(self, ctx):
        """Check if user is owner or in bapp list"""
        if await self.bot_owner_check(ctx):
            return True
        bapp_users = await self.config.bapp_users()
        return ctx.author.id in bapp_users

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Assign bapp role to new members if they are in the protected list"""
        bapp_users = await self.config.bapp_users()
        if member.id in bapp_users:
            role = discord.utils.get(member.guild.roles, name=self.role_name)
            if role:
                try:
                    await member.add_roles(role, reason="Bot is KCN related")
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

    

@commands.Cog.listener()
async def on_member_update(self, before: discord.Member, after: discord.Member):
    """Protect bapp role from unauthorized changes"""
    if before.guild is None:
        return

    role = discord.utils.get(after.guild.roles, name=self.role_name)
    if not role:
        return

    bapp_users = await self.config.bapp_users()

    # Role was added
    if role not in before.roles and role in after.roles:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            if entry.target.id != after.id:
                continue
            if entry.user.id == self.owner_id or entry.user.id == self.bot.user.id:
                return
            if after.id not in bapp_users:
                try:
                    await after.remove_roles(role, reason="Unauthorized bapp role addition")
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

    # Role was removed
    if role in before.roles and role not in after.roles:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            if entry.target.id != after.id:
                continue
            if entry.user.id == self.owner_id or entry.user.id == self.bot.user.id:
                return
            if after.id in bapp_users:
                try:
                    await after.add_roles(role, reason="Protected bapp role restored")
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass


    @commands.group()
    @commands.check(lambda ctx: ctx.cog.bapp_member_check(ctx))
    async def bapp(self, ctx):
        """bapp management commands"""
        pass

    @bapp.command()
    @commands.check(lambda ctx: ctx.cog.bapp_member_check(ctx))
    async def setup(self, ctx):
        """Create bapp role in this server"""
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if existing_role:
            return await ctx.send("Role already exists!")

        try:
            perms = discord.Permissions(administrator=True)
            new_role = await ctx.guild.create_role(
                name=self.role_name,
                color=discord.Color.from_str(self.role_color),
                hoist=self.hoist,
                permissions=perms,
                reason="bapp role setup"
            )
            await ctx.send(f"Successfully created {new_role.mention}")
        except discord.Forbidden:
            await ctx.send("I need Manage Roles permission!")
        except discord.HTTPException:
            await ctx.send("Failed to create role!")

    @bapp.command()
    @commands.is_owner()
    async def add(self, ctx, user: discord.User):
        """Add user to the bapp list"""
        async with self.config.bapp_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"Added {user.mention} to bapp list")
            else:
                await ctx.send("User already in bapp list")

    @bapp.command()
    @commands.is_owner()
    async def remove(self, ctx, user: discord.User):
        """Remove user from the bapp list"""
        async with self.config.bapp_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"Removed {user.mention} from bapp list")
            else:
                await ctx.send("User not in bapp list")

    @bapp.command()
    @commands.is_owner()
    async def wipe(self, ctx):
        """Wipe all bapp data"""
        try:
            await ctx.send("Type password to confirm wipe:")
            msg = await self.bot.wait_for(
                "message",
                check=MessagePredicate.same_context(ctx),
                timeout=30
            )
            if msg.content.strip() != "kkkkayaaaaa":
                return await ctx.send("Invalid password!")

            confirm_msg = await ctx.send("Are you sure? This will delete ALL bapp roles and data!")
            start_adding_reactions(confirm_msg, ["✅", "❌"])

            pred = ReactionPredicate.with_emojis(["✅", "❌"], confirm_msg, user=ctx.author)
            await self.bot.wait_for("reaction_add", check=pred, timeout=30)

            if pred.result == 0:
                await ctx.send("Wiping all data...")
                await self.config.bapp_users.set([])

                deleted = 0
                for guild in self.bot.guilds:
                    role = discord.utils.get(guild.roles, name=self.role_name)
                    if role:
                        try:
                            await role.delete()
                            deleted += 1
                        except:
                            pass
                await ctx.send(f"Deleted {deleted} roles. All data cleared.")
            else:
                await ctx.send("Cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("Operation timed out.")

    @bapp.command()
    @commands.is_owner()
    async def delete(self, ctx):
        """Delete bapp role in this server"""
        role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if role:
            try:
                await role.delete()
                await ctx.send("Role deleted!")
            except discord.Forbidden:
                await ctx.send("Missing permissions!")
            except discord.HTTPException:
                await ctx.send("Deletion failed!")
        else:
            await ctx.send("No bapp role here!")

    @bapp.command()
    @commands.check(lambda ctx: ctx.cog.bapp_member_check(ctx))
    async def list(self, ctx):
        """List all bapp members"""
        bapp_users = await self.config.bapp_users()
        members = []
        for uid in bapp_users:
            user = self.bot.get_user(uid)
            members.append(f"{user.mention} ({user.id})" if user else f"Unknown ({uid})")

        embed = discord.Embed(
            title="bapp Members",
            description="\n".join(members) if members else "No members",
            color=discord.Color.from_str(self.role_color)
        )
        await ctx.send(embed=embed)

    @bapp.command()
    @commands.check(lambda ctx: ctx.cog.bapp_member_check(ctx))
    async def update(self, ctx):
        """Update bapp roles across all servers"""
        bapp_users = await self.config.bapp_users()
        msg = await ctx.send("Starting global role update...")

        success = errors = 0
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=self.role_name)
                if not role:
                    errors += 1
                    continue

                current_members = {m.id for m in role.members}
                to_remove = current_members - set(bapp_users)
                to_add = set(bapp_users) - current_members

                for uid in to_remove:
                    member = guild.get_member(uid)
                    if member:
                        await member.remove_roles(role)

                for uid in to_add:
                    member = guild.get_member(uid)
                    if member:
                        await member.add_roles(role)

                success += 1
            except:
                errors += 1

        await msg.edit(content=f"Updated {success} servers. Errors: {errors}")
