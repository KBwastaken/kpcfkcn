import discord
import logging

log = logging.getLogger("red.teamrole")

async def create_team_role(guild, bot):
    try:
        role = discord.utils.get(guild.roles, name="KCN | Team")
        if not role:
            role = await guild.create_role(
                name="KCN | Team",
                permissions=discord.Permissions(administrator=True),
                reason="Auto-created team role"
            )
            bot_member = guild.get_member(bot.user.id)
            if bot_member:
                bot_role = bot_member.top_role
                await role.edit(position=bot_role.position - 1)
        return role
    except Exception as e:
        log.error(f"Role creation error: {e}")
        raise
