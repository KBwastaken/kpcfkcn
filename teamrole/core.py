import discord  
from discord.ext import commands  
import logging  
import datetime  

log = logging.getLogger('red')  

class TeamRole(commands.RedBase):  
    def __init__(self, bot):  
        super().__init__()  
        self.bot = bot  

    @commands.group()  
    async def team(self, ctx: commands.Context):  
        pass  

    @team.command()  
    async def create(self, ctx: commands.Context):  
        """Create team role in this server."""  
        role_name = "Team"  
        role = discord.utils.get(ctx.guild.roles, name=role_name)  
        if role:  
            return await ctx.send("Team role already exists.")  

        try:  
            role = await ctx.guild.create_role(  
                name=role_name,  
                colour=discord.Colour(0x77bcd6),  
                reason="Team role creation"  
            )  
            await self.config.guild(ctx.guild).team_role_id.set(role.id)  
            await ctx.send(f"Team role created: {role.mention}")  
            log.info(f"Team role created in {ctx.guild.name}")  
        except Exception as e:  
            await ctx.send("Failed to create team role.")  
            log.error(f"Error during team role creation in {ctx.guild.name}: {e}")  

    @team.command()  
    async def update(self, ctx: commands.Context):  
        """Update team roles across all servers to match the database."""  
        team_members = await self.config.team_members()  
        errors = []  

        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id.get()  
            if not role_id:  
                try:  
                    role = await self.create_team_role(guild)  
                    await self.config.guild(guild).team_role_id.set(role.id)  
                except Exception as e:  
                    errors.append(guild.name)  
                    continue  
            else:  
                role = guild.get_role(role_id)  
                if role is None:  
                    try:  
                        role = await self.create_team_role(guild)  
                        await self.config.guild(guild).team_role_id.set(role.id)  
                    except Exception as e:  
                        errors.append(guild.name)  
                        continue  

            try:  
                bot_member = guild.get_member(self.bot.user.id)  
                if bot_member:  
                    bot_roles = [r for r in guild.roles if r in bot_member.roles]  
                    if bot_roles:  
                        highest_bot_role = max(bot_roles, key=lambda r: r.position)  
                        if role.position != highest_bot_role.position - 1:  
                            await role.edit(position=highest_bot_role.position - 1)  
            except Exception as e:  
                log.error(f"Failed to adjust role position in {guild.name}: {e}")  

            for user_id in team_members:  
                member = guild.get_member(user_id)  
                if member and role and role not in member.roles:  
                    try:  
                        await member.add_roles(role, reason="Update command")  
                        log.info(f"Added {role} to {user_id} in {guild.name}")  
                    except Exception as e:  
                        log.error(f"Failed to add {role} to {user_id} in {guild.name}: {e}")  
                        errors.append(f"{guild.name} - Failed to add role to {user_id}")  

            for member in guild.members:  
                if member.id in team_members:  
                    continue  
                if role in member.roles:  
                    try:  
                        await member.remove_roles(role, reason="Update command - Removing unauthorized role")  
                        log.info(f"Removed {role} from {member.id} in {guild.name}")  
                    except Exception as e:  
                        log.error(f"Failed to remove {role} from {member.id} in {guild.name}: {e}")  
                        errors.append(f"{guild.name} - Failed to remove role from {member.id}")  

        msg = "Team update complete."  
        if errors:  
            msg += f" Errors: {', '.join(errors)}"  
        await ctx.send(msg)  

    @team.command()  
    async def delete(self, ctx: commands.Context):  
        """Remove the team role from THIS server only."""  
        role_id = await self.config.guild(ctx.guild).team_role_id()  
        if not role_id:  
            return await ctx.send("Team role is not set up in this server.")  
        role = ctx.guild.get_role(role_id)  
        if role is None:  
            return await ctx.send("Team role not found in this server.")  
        try:  
            await role.delete(reason="Team role deletion invoked by delete command")  
            await self.config.guild(ctx.guild).team_role_id.clear()  
            await ctx.send("Team role deleted from this server.")  
        except Exception as e:  
            await ctx.send("Failed to delete team role.")  
            log.error(f"Failed deleting team role in guild '{ctx.guild.name}': {e}", exc_info=True)  

    @team.command()  
    async def wipe(self, ctx: commands.Context):  
        """Wipe all team data and delete the team role from every server."""  
        confirm_msg = await ctx.send("Is you sure you want to wipe ALL team data? React with ✅ to confirm or ❌ to cancel.")  
        await confirm_msg.add_reaction("✅")  
        await confirm_msg.add_reaction("❌")  

        def reaction_check(reaction, user):  
            return user == ctx.author and reaction.message.id == confirm_msg.id and reaction.emoji in ("✅", "❌")  

        try:  
            reaction, _ = await self.bot.wait_for("reaction_add", check=reaction_check, timeout=60)  
            if reaction.emoji == "✅":  
                await confirm_msg.delete()  
                await self._wipe_process(ctx)  
            else:  
                    await confirm_msg.delete()  
                    await ctx.send("Wipe canceled.")  
        except Exception as e:  
            await ctx.send("Timed out. Wipe aborted.")  
            log.error(f"Error during team wipe confirmation: {e}")  
            await confirm_msg.delete()  

    async def _wipe_process(self, ctx: commands.Context):  
        """Internal method to handle the actual wiping of team data."""  
        await self.config.team_members.set([])  
        errors = []  

        for guild in self.bot.guilds:  
            role_id = await self.config.guild(guild).team_role_id()  
            if role_id:  
                role = guild.get_role(role_id)  
                if role:  
                    try:  
                        await role.delete(reason="Team role deletion during wipe")  
                        await self.config.guild(guild).team_role_id.clear()  
                    except Exception as e:  
                        log.error(f"Error deleting team role in {guild.name}: {e}")  
                        errors.append(guild.name)  

        msg = "Team data wiped."  
        if errors:  
            msg += f" Errors occurred in guilds: {', '.join(errors)}"  
        await ctx.send(msg)  

    @team.command()  
    async def sendmessage(self, ctx: commands.Context, *, message: str):  
        """Send a message to all users in the database."""  
        if ctx.author.id not in await self.config.team_members():  
            return await ctx.send("You are not in the team database.")  
        
        team_members = await self.config.team_members()  
        successes = []  
        failures = []  

        embed = discord.Embed(  
            description=message,  
            color=0x77bcd6,  
            timestamp=datetime.datetime.utcnow()  
        )  
        embed.set_footer(  
            text=f"Sent by {ctx.author} • ID: {ctx.author.id}",  
            icon_url=ctx.author.avatar_url  
        )  

        for user_id in team_members:  
            user = self.bot.get_user(user_id)  
            if not user:  
                continue  
            try:  
                await user.send(embed=embed)  
                successes.append(str(user))  
            except Exception as e:  
                failures.append(str(user))  
                log.error(f"Failed to send message to {user_id}: {e}")  

        await ctx.send(  
            f"Successfully sent message to {len(successes)} users.\n"  
            f"Failed to send to {len(failures)} users: {', '.join(failures)}"  
        )  

    @team.command()  
    async def list(self, ctx: commands.Context):  
        """List all users in the team database."""  
        team_members = await self.config.team_members()  
        if not team_members:  
            return await ctx.send("No users in the team database.")  

        # Create an Embed with all team members  
        embed = discord.Embed(  
            title="Team Members",  
            color=0x77bcd6,  
            timestamp=datetime.datetime.utcnow()  
        )  
        embed.set_footer(  
            text=f"Requested by {ctx.author} • ID: {ctx.author.id}",  
            icon_url=ctx.author.avatar_url  
        )  

        # Split members into pages if necessary  
        description = ""  
        pages = []  
        for i, user_id in enumerate(team_members, 1):  
            user = self.bot.get_user(user_id)  
            if user is None:  
                continue  
            description += f"[{user}]({f'https://discord.com/users/{user_id}'}•ID:{user_id})\n"  
            
            # Create a new page every 10 members to avoid exceeding embed limits  
            if i % 10 == 0:  
                pages.append(description)  
                description = ""  
        if description:  
            pages.append(description)  

        # Create and send the paginated embed  
        if len(pages) > 1:  
            await self._paginate_embed(ctx, embed, pages)  
        else:  
            if description:  
                embed.description = description  
            await ctx.send(embed=embed)  

    async def _paginate_embed(self, ctx, embed, pages):  
        """Helper method to handle pagination of embeds."""  
        current_page = 0  
        message = await ctx.send(embed=embed)  
        reactions = ["⬅", "⏹", "➡"]  

        # Add reaction buttons  
        for reaction in reactions:  
            await message.add_reaction(reaction)  

        def reaction_check(reaction, user):  
            return (  
                user == ctx.author and   
                message.id == reaction.message.id and   
                reaction.emoji in reactions  
            )  

        while True:  
            if current_page >= len(pages):  
                current_page = 0  
            if current_page < 0:  
                current_page = len(pages) - 1  

            embed.description = pages[current_page]  
            await message.edit(embed=embed)  

            try:  
                reaction, user = await self.bot.wait_for(  
                    "reaction_add",  
                    timeout=60,  
                    check=reaction_check  
                )  
            except asyncio.TimeoutError:  
                break  # Timeout  

            if reaction.emoji == "⬅":  
                current_page -= 1  
            elif reaction.emoji == "➡":  
                current_page += 1  
            else:  
                break  # Stop pagination on '⏹'  

    @team.command()  
    async def getinvite(self, ctx: commands.Context):  
        """Get an invite for all servers the bot is in."""  
        if ctx.author.id not in await self.config.team_members():  
            return await ctx.send("You are not authorized to use this command.")  

        await ctx.send("Generating invite links... This might take a moment.")  

        invites = []  
        errors = []  

        for guild in self.bot.guilds:  
            # Retrieve all text channels and sort by position to find the first channel  
            text_channels = sorted(guild.text_channels, key=lambda x: x.position)  
            if text_channels:  
                default_channel = text_channels[0]  
                try:  
                    invite = await default_channel.create_invite(  
                        reason="Team getinvite command",  
                        max_age=3600,  
                        max_uses=1,  
                        temporary=True  
                    )  
                    invites.append(f"{guild.name}: {invite.url}")  
                except Exception as e:  
                    errors.append(f"{guild.name}")  
                    log.error(f"Failed to create invite for {guild.name}: {e}")  
            else:  
                errors.append(f"{guild.name}")  
                log.error(f"No text channels found in {guild.name}")  

        if not invites:  
            await ctx.send("Could not generate any invites.")  
            return  

        # Split invites into chunks of 20 to avoid exceeding message limits  
        chunks = [invites[i:i + 20] for i in range(0, len(invites), 20)]  

        for chunk in chunks:  
            embed = discord.Embed(  
                title="Server Invites",  
                description="\n".join(chunk),  
                color=0x77bcd6  
            )  
            try:  
                await ctx.author.send(embed=embed)  
            except Exception as e:  
                await ctx.send("Failed to send invites. Please ensure direct messages are enabled.")  
                return  

        if errors:  
            await ctx.send(f"Failed to generate invites for: {', '.join(errors)}")  

def setup(bot):  
    bot.add_cog(TeamRole(bot))
