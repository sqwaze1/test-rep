import os
import time
import aiohttp
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
ROLE_ID = int(os.getenv("ROLE_ID", "0"))

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


async def get_game_status(session, universe_id):
    url = f"https://develop.roblox.com/v1/universes/{universe_id}"

    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return False, f"Game {universe_id}"

            data = await resp.json()

            name = data.get("name", f"Game {universe_id}")
            is_active = data.get("isActive", False)
            privacy = data.get("privacyType", "Private")
            root_place = data.get("rootPlaceId")

            link = f"https://www.roblox.com/games/{root_place}"

            if is_active and privacy == "Public":
                return True, name, link

            return False, name, link

    except:
        return False, f"Game {universe_id}", None


async def build_embed_and_check_changes(channel):
    global last_status

    now = int(time.time())
    blocks = []

    async with aiohttp.ClientSession() as session:
        for uid in UNIVERSE_IDS:
            name, status, players, link = await get_game_full_data(session, uid)

            prev = last_status.get(uid)

            if prev is not None and prev != status:
                role_ping = f"<@&{ROLE_ID}>" if ROLE_ID else ""

                if status:
                    await channel.send(
                        f"{role_ping} 🟢 **{name}** восстановлена!\n<t:{now}:F>"
                    )
                else:
                    await channel.send(
                        f"{role_ping} 🔴 **{name}** упала!\n<t:{now}:F>"
                    )

            last_status[uid] = status

            status_text = "Active" if status else "Down"
            icon = "🟢" if status else "🔴"

            block = (
                f"🛒 **{name}**\n"
                f"> * Game Status: {status_text} {icon}\n"
                f"> * Online: {players} 👥\n"
                f"> * Last Update: <t:{now}:R> 🕐\n"
                f"[JOIN GAME]({link}) 👈\n"
            )

            blocks.append(block)

    embed = discord.Embed(
        title="🎮 Games Monitor",
        description="\n".join(blocks),
        color=0x2ecc71
    )

    return embed


@tasks.loop(seconds=120)
async def update_status():
    global message_id

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    embed = await build_embed_and_check_changes(channel)

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
