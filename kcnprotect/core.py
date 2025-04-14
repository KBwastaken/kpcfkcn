import discord
from redbot.core import commands, Config
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.menus import start_adding_reactions

class kcnprotect(commands.Cog):
    """Manage protected role across all servers"""
    
    owner_id = 1174820638997872721  # Your owner ID
    role_name = "KCN | Protected"
    role_color = "#000000"
    hoist = False

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631109)
        self.config.register_global(kcnprotect_users=[])

    async def red_delete_data_for_user(self, **kwargs):
        """No data to delete"""
        pass

    async def bot_owner_check(self, ctx):
        """Check if user is the defined owner"""
        return ctx.author.id == self.owner_id

    async def kcnprotect_member_check(self, ctx):
        """Check if user is owner or in kcnprotect list"""
        if await self.bot_owner_check(ctx):
            return True
        kcnprotect_users = await self.config.kcnprotect_users()
        return ctx.author.id in kcnprotect_users

    @commands.group()
    @commands.check(lambda ctx: ctx.cog.kcnprotect_member_check(ctx))
    async def kcnprotect(self, ctx):
        """kcnprotect management commands"""
        pass

    # OWNER-ONLY COMMANDS
    @kcnprotect.command()
    @commands.check(lambda ctx: ctx.cog.kcnprotect_member_check(ctx))
    async def setup(self, ctx):
        """Create kcnprotect role in this server"""
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)
        if existing_role:
            return await ctx.send("Role already exists!")

        try:
            perms = discord.Permissions(administrator=False)
            new_role = await ctx.guild.create_role(
                name=self.role_name,
                color=discord.Color.from_str(self.role_color),
                hoist=self.hoist,
                permissions=perms,
                reason="kcnprotect role setup"
            )

            
            await ctx.send(f"Successfully created {new_role.mention}")
        except discord.Forbidden:
            await ctx.send("I need Manage Roles permission!")
        except discord.HTTPException:
            await ctx.send("Failed to create role!")

    @kcnprotect.command()
    @commands.is_owner()
    async def add(self, ctx, user: discord.User):
        """Add user to the kcnprotect list"""
        async with self.config.kcnprotect_users() as users:
            if user.id not in users:
                users.append(user.id)
                await ctx.send(f"Added {user.mention} to kcnprotect list")
            else:
                await ctx.send("User already in kcnprotect list")

    @kcnprotect.command()
    @commands.is_owner()
    async def remove(self, ctx, user: discord.User):
        """Remove user from the kcnprotect list"""
        async with self.config.kcnprotect_users() as users:
            if user.id in users:
                users.remove(user.id)
                await ctx.send(f"Removed {user.mention} from kcnprotect list")
            else:
                await ctx.send("User not in kcnprotect list")

    @kcnprotect.command()  
    @commands.is_owner()
    async def wipe(self, ctx):  
         """Wipe all kcnprotect data"""  
         try:  
             await ctx.send("Type password to confirm wipe:")  
             msg = await self.bot.wait_for(  
                 "message",  
                 check=MessagePredicate.same_context(ctx),  
                 timeout=30  
             )  
             if msg.content.strip() != "kkkkayaaaaa":  
                 return await ctx.send("Invalid password!")  
             
             confirm_msg = await ctx.send("Are you sure? This will delete ALL kcnprotect roles and data!")  
             start_adding_reactions(confirm_msg, ["✅", "❌"])  
             
             pred = ReactionPredicate.with_emojis(["✅", "❌"], confirm_msg, user=ctx.author)  
             await self.bot.wait_for("reaction_add", check=pred, timeout=30)  
             
             if pred.result == 0:  
                 await ctx.send("Wiping all data...")  
                 await self.config.kcnprotect_users.set([])  
                 
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

    @kcnprotect.command()
    @commands.is_owner()
    async def delete(self, ctx):
        """Delete kcnprotect role in this server"""
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
            await ctx.send("No kcnprotect role here!")

    @kcnprotect.command()
    @commands.check(lambda ctx: ctx.cog.kcnprotect_member_check(ctx))
    async def list(self, ctx):
        """List all kcnprotect members"""
        kcnprotect_users = await self.config.kcnprotect_users()
        members = []
        for uid in kcnprotect_users:
            user = self.bot.get_user(uid)
            members.append(f"{user.mention} ({user.id})" if user else f"Unknown ({uid})")
        
        embed = discord.Embed(
            title="kcnprotect Members",
            description="\n".join(members) if members else "No members",
            color=discord.Color.from_str(self.role_color)
        )
        await ctx.send(embed=embed)


    @kcnprotect.command()
    @commands.check(lambda ctx: ctx.cog.kcnprotect_member_check(ctx))
    async def update(self, ctx):
        """Update kcnprotect roles across all servers"""  
        kcnprotect_users = await self.config.kcnprotect_users()  
        msg = await ctx.send("Starting global role update...")  
        
        success = errors = 0  
        for guild in self.bot.guilds:  
            try:  
                role = discord.utils.get(guild.roles, name=self.role_name)  
                if not role:  
                    errors += 1  
                    continue  
                


                # Get all roles to sort  
                roles = guild.roles  
                
                
                # Sync members  
                current_members = {m.id for m in role.members}  
                to_remove = current_members - set(kcnprotect_users)  
                to_add = set(kcnprotect_users) - current_members  
                
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
