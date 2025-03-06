import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class TeamRole(commands.Cog):
    """Manage team role across all servers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(team_users=[])

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete"""
        pass

    @commands.group()
    @commands.is_owner()
    async def team(self, ctx):
        """Team management commands"""
        pass

    @team.command()
    async def setup(self, ctx):
        """Create team role in this server"""
        role_name = "KCN | Team"
        color = discord.Color.from_str("#77bcd6")
        
        existing_role = discord.utils.get(ctx.guild.roles, name=role_name)
        if existing_role:
            return await ctx.send("Role already exists!")
            
        try:
            perms = discord.Permissions(administrator=True)
            new_role = await ctx.guild.create_role(
                name=role_name,
                color=color,
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
                role = discord.utils.get(guild.roles, name="KCN | Team")
                if not role:
                    await ctx.send(f"{guild.name} ({guild.id}): Server not setup")
                    errors += 1
                    continue
                
                # Role positioning with proper handling
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
                
                # Remove users not in list
                to_remove = [m for m in role.members if m.id not in team_users]
                for member in to_remove:
                    await member.remove_roles(role)
                
                # Add missing users
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
                    role = discord.utils.get(guild.roles, name="KCN | Team")
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
        role = discord.utils.get(ctx.guild.roles, name="KCN | Team")
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

async def setup(bot):
    await bot.add_cog(TeamRole(bot))
