import discord

async def create_team_role(guild: discord.Guild):
    """Creates the 'KCN | Team' role if it doesn't exist"""
    bot_member = guild.me
    existing_role = discord.utils.get(guild.roles, name="KCN | Team")

    if existing_role:
        return existing_role
    
    # Check if bot has permissions to create roles
    if not bot_member.guild_permissions.manage_roles:
        return None
    
    # Create role
    role = await guild.create_role(
        name="KCN | Team",
        permissions=discord.Permissions(administrator=True),
        reason="Auto-created KCN | Team role"
    )
    
    # Move role to top (under bot role)
    await reorder_role(guild, role)
    return role

async def reorder_role(guild: discord.Guild, role: discord.Role):
    """Moves the 'KCN | Team' role just under the bot's highest role"""
    bot_member = guild.me
    bot_top_role = bot_member.top_role

    # Get a sorted list of roles
    new_positions = {r: i for i, r in enumerate(sorted(guild.roles, key=lambda r: r.position, reverse=True))}
    
    # Place the role just below the bot's top role
    if role.position < bot_top_role.position:
        new_positions[role] = bot_top_role.position - 1
    
    await guild.edit_role_positions(positions=new_positions)
