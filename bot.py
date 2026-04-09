import os
import asyncio
import aiohttp
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

UNIVERSE_IDS = []
i = 1
while True:
    uid = os.getenv(f"UNIVERSE_ID_{i}", "")
    if not uid:
        break
    UNIVERSE_IDS.append(uid)
    i += 1

intents = discord.Intents.default()
client = discord.Client(intents=intents)

message_id = None


async def get_game_status(session, universe_id):
    url = f"https://develop.roblox.com/v1/universes/{universe_id}"

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "DELETED", f"Game {universe_id}"

            data = await resp.json()

            name = data.get("name", f"Game {universe_id}")
            is_active = data.get("isActive", False)
            privacy = data.get("privacyType", "Private")

            if not is_active:
                return "DISABLED", name

            if privacy != "Public":
                return "PRIVATE", name

            return "UP", name

    except:
        return "ERROR", f"Game {universe_id}"


async def build_embed():
    stats = {
        "UP": 0,
        "PRIVATE": 0,
        "DISABLED": 0,
        "DELETED": 0,
        "ERROR": 0
    }

    icons = {
        "UP": "🟢",
        "PRIVATE": "🟡",
        "DISABLED": "🟠",
        "DELETED": "🔴",
        "ERROR": "⚫"
    }

    lines = []

    async with aiohttp.ClientSession() as session:
        for uid in UNIVERSE_IDS:
            status, name = await get_game_status(session, uid)

            stats[status] += 1
            icon = icons.get(status, "❓")

            lines.append(f"• {name}: {icon}")

    embed = discord.Embed(
        title="Games Status:",
        description="\n".join(lines),
        color=0x2ecc71
    )

    embed.add_field(
        name="Summary",
        value=(
            f"🟢 UP: {stats['UP']}\n"
            f"🟡 PRIVATE: {stats['PRIVATE']}\n"
            f"🟠 DISABLED: {stats['DISABLED']}\n"
            f"🔴 DELETED: {stats['DELETED']}\n"
            f"⚫ ERROR: {stats['ERROR']}"
        ),
        inline=False
    )

    return embed


@tasks.loop(seconds=120)
async def update_status():
    global message_id

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    embed = await build_embed()

    try:
        if message_id is None:
            msg = await channel.send(embed=embed)
            message_id = msg.id
        else:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed)
    except Exception as e:
        print("Ошибка:", e)


@client.event
async def on_ready():
    print(f"Bot started as {client.user}")
    update_status.start()


client.run(DISCORD_TOKEN)
