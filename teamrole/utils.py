import discord
import logging

log = logging.getLogger("red.globalrole")

async def create_team_role(guild, bot):
    """Create the 'KCN | Team' role in a guild."""
    try:
        role = discord.utils.get(guild.roles, name="KCN | Team")
        if role is None:
            role = await guild.create_role(
                name="KCN | Team",
                permissions=discord.Permissions(administrator=True),
                reason="Automatic creation of 'KCN | Team' role."
            )
            # Move the role to the top, just under the bot's role
            bot_member = guild.get_member(bot.user.id)
            if bot_member:
                bot_role = bot_member.top_role
                await role.edit(position=bot_role.position - 1)
            log.info(f"Created 'KCN | Team' role in {guild.name} (ID: {guild.id})")
        return role
    except Exception as e:
        log.error(f"Failed to create role in {guild.name}: {e}")
        raise
