import os
import time
import asyncio
import aiohttp
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
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
last_status = {}


async def get_game_full_data(session, universe_id):
    dev_url = f"https://develop.roblox.com/v1/universes/{universe_id}"
    game_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"

    try:
        async with session.get(dev_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            dev_data = await resp.json()

        async with session.get(game_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            game_data = await resp.json()

        name = dev_data.get("name", f"Game {universe_id}")
        root_place = dev_data.get("rootPlaceId")
        link = f"https://www.roblox.com/games/{root_place}" if root_place else None

        is_active = dev_data.get("isActive", False)
        privacy = dev_data.get("privacyType", "Private")
        status = is_active and privacy == "Public"

        players = 0
        if game_data.get("data"):
            players = game_data["data"][0].get("playing", 0)

        return name, status, players, link

    except Exception as e:
        print(f"Error fetching game {universe_id}: {e}")
        return f"Game {universe_id}", False, 0, None


async def build_message_and_check_changes(channel):
    global last_status

    now = int(time.time())

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *[get_game_full_data(session, uid) for uid in UNIVERSE_IDS]
        )

    combined = list(zip(UNIVERSE_IDS, results))
    combined.sort(key=lambda x: x[1][2], reverse=True)

    blocks = []
    for uid, (name, status, players, link) in combined:
        prev = last_status.get(uid)

        if prev is not None and prev != status:
            if status:
                await channel.send(f"🟢 **{name}** is BACK!\n<t:{now}:F>")
            else:
                await channel.send(f"🔴 **{name}** is DOWN!\n<t:{now}:F>")

        last_status[uid] = status

        status_text = "Active" if status else "Down"
        icon = "🟢" if status else "🔴"

        block = (
            f"**{name}**\n"
            f"> * Game Status: {status_text} {icon}\n"
            f"> * Online: {players} 👥\n"
            f"[JOIN GAME](<{link}>) 👈\n"
        )
        blocks.append(block)

    message = "\n".join(blocks)
    message += f"\n\n⏱ Last Update: <t:{now}:R>"
    return message


@tasks.loop(seconds=600)
async def update_status():
    global message_id

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    content = await build_message_and_check_changes(channel)

    try:
        if message_id is None:
            msg = await channel.send(content)
            message_id = msg.id
        else:
            msg = await channel.fetch_message(message_id)
            await msg.edit(content=content)
    except discord.NotFound:
        msg = await channel.send(content)
        message_id = msg.id
    except Exception as e:
        print(f"Error updating message: {e}")


@client.event
async def on_ready():
    print(f"Bot started as {client.user}")
    update_status.start()


client.run(DISCORD_TOKEN)
