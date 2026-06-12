import asyncio
import discord
from discord.ext import commands
from config import DISCORD_TOKEN, GUILD_ID

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.recruit",
]


@bot.event
async def on_ready():
    print(f"봇 로그인: {bot.user} (ID: {bot.user.id})")
    try:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"슬래시 커맨드 동기화 완료: {[c.name for c in synced]}")
    except Exception as e:
        print(f"동기화 실패: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    print(f"커맨드 에러: {error}")
    try:
        await interaction.response.send_message(f"오류: {error}", ephemeral=True)
    except Exception:
        pass


async def main():
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
