# === FILE: modules/youtube.py ===
"""
YouTube downloader helper module using pytube.
- Supports Audio / Video download
- Async-friendly (ThreadPoolExecutor)
- Returns metadata (title, author, duration, url)
- Ready to integrate with Telegram bot
"""

import re
import os
import time
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from pyrogram.types import InlineKeyboardMarkup
from pytube import YouTube

# Improved pattern to detect YouTube links
YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(m\.)?(youtube\.com|youtu\.be)/"
    r"(watch\?v=[\w\-]{11}|shorts/[\w\-]{11}|embed/[\w\-]{11}|v/[\w\-]{11}|[\w\-]{11})",
    re.IGNORECASE,
)

# Thread pool for blocking downloads
DOWNLOAD_WORKERS = ThreadPoolExecutor(max_workers=2)


def detect_platform(text: str) -> Optional[str]:
    if not text:
        return None
    if YOUTUBE_REGEX.search(text):
        return "youtube"
    return None


async def run_blocking(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(DOWNLOAD_WORKERS, lambda: func(*args, **kwargs))


def _pytube_download(url: str, mode: str, output_dir: str):
    """Blocking download via pytube. Returns {'filepath': path, 'metadata': {...}}"""
    os.makedirs(output_dir, exist_ok=True)

    try:
        yt = YouTube(url)
    except Exception as e:
        raise Exception(f"❌ Failed to fetch video info: {e}")

    if mode == "audio":
        stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
        if not stream:
            raise Exception("❌ No audio streams found")
    else:
        stream = yt.streams.get_highest_resolution()
        if not stream:
            raise Exception("❌ No video streams found")

    try:
        filepath = stream.download(output_path=output_dir)
    except Exception as e:
        raise Exception(f"❌ Failed to download: {e}")

    metadata = {
        "filepath": filepath,
        "title": yt.title,
        "uploader": yt.author,
        "duration": yt.length,  # in seconds
        "webpage_url": url
    }

    return {"filepath": filepath, "metadata": metadata}


async def download_and_send(
    client,
    chat_id: int,
    url: str,
    mode: str,
    requester,
    processing_message,
    developer_markup: InlineKeyboardMarkup,
    downloads_dir: str = "downloads",
):
    start_ts = time.time()
    try:
        res = await run_blocking(_pytube_download, url, mode, downloads_dir)
        filepath = res.get("filepath")
        metadata = res.get("metadata", {})

        if not filepath or not os.path.exists(filepath):
            await client.send_message(chat_id, "❌ Download failed or file not found.")
            await safe_delete(processing_message)
            return

        requester_mention = f"[{escape_md(requester.first_name)}](tg://user?id={requester.id})"
        caption_lines = [f"**{escape_md(metadata.get('title') or 'Unknown title')}**"]
        if metadata.get("uploader"):
            caption_lines.append(f"Uploader: {escape_md(metadata['uploader'])}")
        if metadata.get("duration") is not None:
            caption_lines.append(f"Duration: {format_seconds(metadata['duration'])}")
        caption_lines.append(f"Requested by: {requester_mention}")
        caption_lines.append(f"Source: {escape_md(metadata.get('webpage_url'))}")
        caption = "\n".join(caption_lines)

        if mode == "audio":
            await client.send_audio(
                chat_id,
                audio=filepath,
                caption=caption,
                reply_markup=developer_markup,
                parse_mode="markdown",
            )
        else:
            await client.send_video(
                chat_id,
                video=filepath,
                caption=caption,
                supports_streaming=True,
                reply_markup=developer_markup,
                parse_mode="markdown",
            )

        await safe_delete(processing_message)

        try:
            os.remove(filepath)
        except Exception:
            pass

        elapsed = int(time.time() - start_ts)
        await client.send_message(chat_id, f"✅ Uploaded in {elapsed}s.")

    except Exception as e:
        await safe_delete(processing_message)
        await client.send_message(chat_id, str(e))


async def safe_delete(message):
    try:
        if message:
            await message.delete()
    except Exception:
        pass


def format_seconds(seconds):
    try:
        s = int(seconds)
    except Exception:
        return "Unknown"
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def escape_md(text: str) -> str:
    if not text:
        return ""
    for ch in "_`*[]()#:+-=~|{}.!>":
        text = text.replace(ch, f"\\{ch}")
    return text


def register_youtube_handlers(app):
    pass
