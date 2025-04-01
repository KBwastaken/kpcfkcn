import discord
import asyncio
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

    @team.command()
    @commands.is_owner()
    async def setup(self, ctx):
        """Create team role and private channels in this server"""
        await ctx.send("🔧 **Starting setup...**")

        # Check bot permissions
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send("❌ **Error:** I need `Manage Roles` permission!", delete_after=120)
        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("❌ **Error:** I need `Manage Channels` permission!", delete_after=120)

        # Check if role already exists
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if existing_role:
            return await ctx.send("⚠️ **Role already exists!** Skipping role creation.", delete_after=30)

        try:
            await ctx.send("⏳ **Creating role...**", delete_after=30)
            perms = discord.Permissions(administrator=True)
            new_role = await ctx.guild.create_role(
                name=self.role_name,
                color=discord.Color.from_str(self.role_color),
                permissions=perms,
                reason="Team role setup"
            )
            await ctx.send(f"✅ **Role created:** {new_role.mention}", delete_after=60)

            # Move role below bot's top role
            bot_top_role = ctx.guild.me.top_role
            if bot_top_role and new_role.position < bot_top_role.position - 1:
                await new_role.edit(position=bot_top_role.position - 1)
                await ctx.send("✅ **Role positioned correctly!**", delete_after=30)

            # Create private category and channels
            await ctx.send("⏳ **Creating private category...**", delete_after=30)

            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                new_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }

            category = await ctx.guild.create_category("KCN", overwrites=overwrites)
            if category:
                await ctx.send(f"✅ **Category created:** `{category.name}`", delete_after=30)
            else:
                return await ctx.send("❌ **Error:** Failed to create category!", delete_after=120)

            channels = [ "general","cmd", "alerts", "transcripts", "kcn-logs"]
            cmd_channel = None

            for channel_name in channels:
                await ctx.send(f"⏳ **Creating channel:** `{channel_name}`...")
                channel = await ctx.guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

                if channel:
                    await ctx.send(f"✅ **Channel created:** {channel.mention}", delete_after=30)
                else:
                    await ctx.send(f"❌ **Error:** Failed to create `{channel_name}`", delete_after=120)

        except discord.Forbidden:
            await ctx.send("❌ **Error:** I need `Manage Roles` and `Manage Channels` permissions!", delete_after=120)
        except discord.HTTPException as e:
            await ctx.send(f"❌ **Error:** Failed to create role or channels! `{e}`", delete_after=120)

        await ctx.send("**Setup complete!**")

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
                 await ctx.send(f"Deleted {deleted} roles. All data cleared.")  
             else:  
                 await ctx.send("Cancelled.")  
         except TimeoutError:  
             await ctx.send("Operation timed out.")  

    @team.command()
    @commands.is_owner()
    async def delete(self, ctx):
        """Delete team role, category, and channels in this server"""
        await ctx.send("🛑 **Starting deletion process...**")

        role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        category = discord.utils.get(ctx.guild.categories, name="KCN")

        # Delete role
        if role:
            try:
                await ctx.send(f"⏳ **Deleting role:** {role.name}...")
                await role.delete()
                await ctx.send("✅ **Role deleted!**", delete_after=30)
            except discord.Forbidden:
                return await ctx.send("❌ **Error:** Missing permissions to delete role!", delete_after=120)
            except discord.HTTPException as e:
                return await ctx.send(f"❌ **Error:** Failed to delete role! `{e}`", delete_after=120)
        else:
            await ctx.send("⚠️ **No team role found. Skipping role deletion.**", delete_after=120)

        # Delete category and channels
        if category:
            try:
                await ctx.send(f"⏳ **Deleting category:** {category.name} and its channels...", delete_after=30)

                for channel in category.channels:
                    try:
                        await channel.delete()
                        await ctx.send(f"✅ **Deleted channel:** #{channel.name}", delete_after=30)
                    except discord.Forbidden:
                        await ctx.send(f"❌ **Error:** Missing permissions to delete `{channel.name}`", delete_after=120)
                    except discord.HTTPException as e:
                        await ctx.send(f"❌ **Error:** Failed to delete `{channel.name}`! `{e}`", delete_after=120)

                await category.delete()
                await ctx.send(f"✅ **Category deleted:** {category.name}", delete_after=30)

            except discord.Forbidden:
                await ctx.send("❌ **Error:** Missing permissions to delete category!", delete_after=120)
            except discord.HTTPException as e:
                await ctx.send(f"❌ **Error:** Failed to delete category! `{e}`", delete_after=120)
        else:
            await ctx.send("⚠️ **No category named 'KCN' found. Skipping category deletion.**", delete_after=120)

        await ctx.send("🎉 **Deletion process complete!**")


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
