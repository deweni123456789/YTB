#!/usr/bin/env python3
# === FILE: main.py ===
"""Optimized Telegram YouTube downloader bot (Pyrogram).
Features:
- Detects YouTube links and shows Audio / Video inline buttons
- Uses modules/youtube.py for downloading via yt-dlp (FFMPEG & cookies support)
- Sends file with metadata, requester mention and Developer button
- Cleans up processing & optional service messages
- Docker-friendly (use env vars)
"""

import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.youtube import register_youtube_handlers, detect_platform, download_and_send

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DOWNLOADS_DIR = os.getenv("DOWNLOADS_DIR", "downloads")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

app = Client(
    "yt_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="/app"
)

def developer_button():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Developer (@deweni2)", url="https://t.me/deweni2")]]
    )

# Start / Help
@app.on_message(filters.command(["start", "help"]) & filters.private)
async def start(_, message):
    await message.reply(
        "Send a YouTube link and choose Audio or Video.\n"
        "I will download and upload the file with metadata.\nDeveloper: @deweni2"
    )

# Detect YouTube links in private chat and present buttons
@app.on_message(filters.private & filters.text)
async def handle_text(_, message):
    text = message.text.strip()
    platform = detect_platform(text)
    if platform == "youtube":

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 Audio", callback_data=f"yt|audio|{message.message_id}"),
                InlineKeyboardButton("🎬 Video", callback_data=f"yt|video|{message.message_id}"),
            ],
            [InlineKeyboardButton("Developer (@deweni2)", url="https://t.me/deweni2")],
        ])

        # Reply with selection buttons
        await message.reply("Choose download type:", reply_markup=buttons)
    else:
        await message.reply("No supported YouTube link detected. Send a YouTube URL.")


# Callback handler for inline buttons (audio/video)
@app.on_callback_query(filters.regex(r"^yt\|(?:audio|video)\|\d+$"))
async def callback_download(client, callback_query):
    try:
        data = callback_query.data.split("|")
        mode = data[1]
        orig_msg_id = int(data[2])

        chat_id = callback_query.message.chat.id

        # Try to fetch the original message containing the URL
        original = None
        try:
            original = await client.get_messages(chat_id, orig_msg_id)
        except Exception:
            original = callback_query.message.reply_to_message

        if not original or not getattr(original, 'text', None):
            await callback_query.answer("Original link not found.", show_alert=True)
            return

        url = original.text.strip()
        await callback_query.answer(f"Preparing {mode} download...")

        # Send a processing message
        processing = await client.send_message(chat_id, "⏳ Processing... Please wait.")

        # Kick off download and send
        await download_and_send(
            client=client,
            chat_id=chat_id,
            url=url,
            mode=mode,
            requester=callback_query.from_user,
            processing_message=processing,
            developer_markup=developer_button(),
            downloads_dir=DOWNLOADS_DIR,
        )

    except Exception as e:
        try:
            await callback_query.message.reply(f"Error: {e}")
        except Exception:
            pass

# Optional: delete service messages in groups (if bot is admin)
@app.on_message(filters.service)
async def service_cleanup(_, message):
    try:
        # only attempt to delete if bot is admin and it's a group/channel service message
        await message.delete()
    except Exception:
        pass

if __name__ == "__main__":
    register_youtube_handlers(app)
    print("Starting bot...")
    app.run()
