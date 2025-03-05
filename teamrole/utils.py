import discord  
import logging  

log = logging.getLogger("red.teamrole")  

async def create_team_role(guild, bot) -> discord.Role:  
    """Create 'KCN | Team' role with administrative permissions."""  
    try:  
        role = discord.utils.get(guild.roles, name="KCN | Team")  
        if not role:  
            role = await guild.create_role(  
                name="KCN | Team",  
                permissions=discord.Permissions(administrator=True),  
                reason="Auto-create team role"  
            )  
            # Position the role just below the bot's top role.  
            bot_member = guild.get_member(bot.user.id)  
            if bot_member:  
                # Ensure that the new role is placed below the bot's highest role.  
                await role.edit(position=bot_member.top_role.position - 1)  
        return role  
    except Exception as e:  
        log.error(f"Failed creating role in {guild.name}: {e}", exc_info=True)  
        raise
