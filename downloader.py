#!/usr/bin/env python3
"""
Telegram Movie Downloader Bot (MTProto / Telethon)
--------------------------------------------------
Forward any file/movie/media to this bot and it downloads it to OUTPUT_DIR.

Why MTProto (Telethon) instead of the cloud Bot API:
  - Cloud Bot API caps bot downloads at ~20 MB -> useless for movies.
  - An MTProto session has NO practical size cap (2GB+ movies work).
  - No Docker, no extra "local Bot API server" process needed.

Run on the HOST (so it can see /media/devmon/...).
"""
import asyncio
import logging
import os
from pathlib import Path

from telethon import TelegramClient, events

# ------------------------------------------------------------------------
# CONFIG — set these (see README)
# ------------------------------------------------------------------------
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")   # from @BotFather
OUTPUT_DIR = Path(os.environ.get("TG_OUTPUT_DIR", "/media/devmon/sda1-usb-Kingston_DataTra"))
SESSION_DIR = Path(os.environ.get("TELEGRAM_SESSION", "."))
SESSION_FILE = str(SESSION_DIR / Path(os.environ.get("TELEGRAM_SESSION_NAME", "tgdl_session")))

# Passwords / admin: only this user id can command the bot (optional).
# Set ALLOWED_USER_ID to your numeric Telegram id to lock it down. 0 = allow anyone private.
ALLOWED_USER_ID = int(os.environ.get("TG_ALLOWED_USER_ID", "0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("tgdl")

# Sanitize a filename so it's safe on disk.
def safe_name(name: str) -> str:
    keep = []
    for ch in name or "file":
        if ch.isalnum() or ch in " ._()-[]":
            keep.append(ch)
        else:
            keep.append("_")
    s = "".join(keep).strip()
    return s or "file"


async def download_media(event: events.NewMessage.Event) -> str:
    """Download an entity's media into OUTPUT_DIR. Returns saved path string."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Telegram's pretty filename (e.g. "Movie.2024.1080p.mkv")
    base = getattr(event.message.file, "name", None) or f"media_{event.message.id}"
    name = safe_name(str(base))
    path = OUTPUT_DIR / name

    # Path collision -> append a counter.
    n = 1
    while path.exists():
        path = OUTPUT_DIR / (Path(name).stem + f" ({n})" + Path(name).suffix)
        n += 1

    log.info("Downloading '%s' -> %s ...", name, path)
    status = await client.download_media(
        event.message, file=str(path), progress_callback=progress
    )
    return str(status or path)


def progress(current: int, total: int) -> None:
    if total:
        pct = current / total * 100
        log.info("  -> %5.1f%%  (%s / %s MB)", pct, current // 1_048_576, total // 1_048_576)


async def handler(event: events.NewMessage.Event) -> None:
    uid = event.from_id.user_id if event.from_id else None
    if ALLOWED_USER_ID and uid != ALLOWED_USER_ID:
        await event.reply("Not authorised.")
        return

    txt = (event.raw_text or "").strip()

    if txt == "/start":
        await event.reply(
            "Movie downloader ready 📥\n"
            f"Saving to: `{OUTPUT_DIR}`\n"
            "Forward any file/movie here and I'll grab it."
        )
        return

    if event.media:
        await event.reply("Got it, downloading… ⏳")
        try:
            saved = await download_media(event)
            size = Path(saved).stat().st_size / 1_048_576 if Path(saved).exists() else 0
            await event.reply(
                f"Done ✅ saved:\n`{saved}`\n({size:,.1f} MB)"
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("download failed")
            await event.reply(f"Failed ❌ {exc}")
    else:
        await event.reply("Send or forward a media file (video/document/photo).")


async def main() -> None:
    global client
    if API_ID == 0 or not API_HASH or not BOT_TOKEN:
        raise SystemExit(
            "Missing config. Set TG_API_ID, TG_API_HASH, TG_BOT_TOKEN (and TG_OUTPUT_DIR)."
        )
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    client.on(events.NewMessage(func=lambda e: e.is_private))(handler)
    await client.start(bot_token=BOT_TOKEN)
    log.info("Bot online as %s. Waiting for forwarded files ...", (await client.get_me()).username)
    log.info("Output dir: %s", OUTPUT_DIR)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())