import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
RECRUIT_FORUM_CHANNEL_ID = int(os.getenv("RECRUIT_FORUM_CHANNEL_ID", 0))
GUILD_ID = int(os.getenv("GUILD_ID", 0))
