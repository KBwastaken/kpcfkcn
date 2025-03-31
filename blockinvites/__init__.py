from .blockinvites import BlockInvites

async def setup(bot):
    await bot.add_cog(BlockInvites(bot))
