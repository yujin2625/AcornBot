import json
import aiohttp
import discord
from discord.ext import commands, tasks
from pathlib import Path

from config import FREE_GAMES_CHANNEL_ID, FREE_GAMES_CHECK_INTERVAL_HOURS

SEEN_PATH = Path("data/seen_games.json")

EPIC_API = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=ko&country=KR&allowCountries=KR"
STEAM_SEARCH_API = "https://store.steampowered.com/api/featuredcategories?cc=KR&l=korean"


def load_seen() -> set:
    if SEEN_PATH.exists():
        with open(SEEN_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(SEEN_PATH, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)


async def fetch_epic_free_games(session: aiohttp.ClientSession) -> list[dict]:
    async with session.get(EPIC_API) as resp:
        data = await resp.json()

    games = []
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    for el in elements:
        promotions = el.get("promotions") or {}
        offers = promotions.get("promotionalOffers", [])
        for offer_group in offers:
            for offer in offer_group.get("promotionalOffers", []):
                discount = offer.get("discountSetting", {}).get("discountPercentage", -1)
                if discount == 0:
                    title = el.get("title", "알 수 없음")
                    slug = el.get("productSlug") or el.get("urlSlug") or ""
                    url = f"https://store.epicgames.com/ko/p/{slug}" if slug else "https://store.epicgames.com/ko/free-games"
                    original_price = el.get("price", {}).get("totalPrice", {}).get("fmtOriginalPrice", "무료")
                    end_date = offer.get("endDate", "")[:10]
                    games.append({
                        "id": f"epic_{el.get('id', title)}",
                        "title": title,
                        "url": url,
                        "original_price": original_price,
                        "end_date": end_date,
                        "store": "Epic Games",
                        "color": 0x2ECC71,
                        "thumbnail": "https://upload.wikimedia.org/wikipedia/commons/3/31/Epic_Games_logo.svg",
                    })
    return games


async def fetch_steam_free_games(session: aiohttp.ClientSession) -> list[dict]:
    # Steam 특가(100% 할인) 게임은 별도 API가 없어 specials 카테고리에서 탐색
    async with session.get(STEAM_SEARCH_API) as resp:
        data = await resp.json()

    games = []
    specials = data.get("specials", {}).get("items", [])
    for item in specials:
        if item.get("discount_percent") == 100:
            app_id = item.get("id")
            title = item.get("name", "알 수 없음")
            original_price = item.get("original_price", 0)
            formatted = f"{original_price // 100:,}원" if original_price else "무료"
            games.append({
                "id": f"steam_{app_id}",
                "title": title,
                "url": f"https://store.steampowered.com/app/{app_id}/",
                "original_price": formatted,
                "end_date": "",
                "store": "Steam",
                "color": 0x1B2838,
                "thumbnail": "https://store.steampowered.com/favicon.ico",
            })
    return games


def build_game_embed(game: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"🆓 {game['title']}",
        url=game["url"],
        color=game["color"],
    )
    embed.add_field(name="🏪 스토어", value=game["store"], inline=True)
    embed.add_field(name="💰 원가", value=game["original_price"], inline=True)
    if game["end_date"]:
        embed.add_field(name="📅 무료 종료일", value=game["end_date"], inline=True)
    embed.add_field(name="🔗 링크", value=f"[지금 받기]({game['url']})", inline=False)
    return embed


class FreeGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_free_games.change_interval(hours=FREE_GAMES_CHECK_INTERVAL_HOURS)
        self.check_free_games.start()

    def cog_unload(self):
        self.check_free_games.cancel()

    @tasks.loop(hours=2)
    async def check_free_games(self):
        forum = self.bot.get_channel(FREE_GAMES_CHANNEL_ID)
        if forum is None or not isinstance(forum, discord.ForumChannel):
            return

        seen = load_seen()
        new_seen = set(seen)

        async with aiohttp.ClientSession() as session:
            epic = await fetch_epic_free_games(session)
            steam = await fetch_steam_free_games(session)

        for game in epic + steam:
            if game["id"] not in seen:
                embed = build_game_embed(game)
                post_title = f"[{game['store']}] 🆓 {game['title']}"
                await forum.create_thread(name=post_title, embed=embed)
                new_seen.add(game["id"])

        save_seen(new_seen)

    @check_free_games.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(FreeGames(bot))
