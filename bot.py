import os
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

            if is_active and privacy == "Public":
                return True, name

            return False, name

    except:
        return False, f"Game {universe_id}"


async def build_embed_and_check_changes(channel):
    global last_status

    up = 0
    down = 0
    lines = []

    async with aiohttp.ClientSession() as session:
        for uid in UNIVERSE_IDS:
            status, name = await get_game_status(session, uid)

            prev = last_status.get(uid)

            if prev is not None and prev != status:
                if status:
                    await channel.send(f"🟢 **{name}** is now UP")
                else:
                    await channel.send(f"🔴 **{name}** is now DOWN")

            last_status[uid] = status

            if status:
                up += 1
                icon = "🟢"
            else:
                down += 1
                icon = "🔴"

            lines.append(f"• {name}: {icon}")

    embed = discord.Embed(
        title="Games Status:",
        description="\n".join(lines),
        color=0x2ecc71
    )

    embed.add_field(
        name="Status Info",
        value=f"🟢 - UP | 🔴 - DOWN\n\n🟢 {up} | 🔴 {down}",
        inline=False
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
