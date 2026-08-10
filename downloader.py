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
import time
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

# Access control: only listed Telegram user ids may use the bot.
# Comma-separated, e.g. "11111,22222". "0" or empty = allow anyone in a private chat.
ALLOWED_USERS = {
    int(x) for x in os.environ.get("TG_ALLOWED_USER_ID", "0").split(",") if x.strip().isdigit()
}

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


def _fmt_size(n: int) -> str:
    """Human-readable size."""
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def _progress_bar(pct: float, width: int = 18) -> str:
    filled = int(round(pct / 100 * width))
    return "█" * filled + "░" * (width - filled)


async def download_media(event: events.NewMessage.Event, status_msg) -> str:
    """Download an entity's media into OUTPUT_DIR, live-updating status_msg.

    The same message is edited in place with a progress bar as it downloads,
    throttled so we don't trip Telegram's "message not modified" / edit limits.
    Returns the saved path string.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Telegram's pretty filename (e.g. "Movie.2024.1080p.mkv")
    base = getattr(event.message.file, "name", None) or f"media_{event.message.id}"
    total = getattr(event.message.file, "size", 0) or 0
    name = safe_name(str(base))
    path = OUTPUT_DIR / name

    # Path collision -> append a counter.
    n = 1
    while path.exists():
        path = OUTPUT_DIR / (Path(name).stem + f" ({n})" + Path(name).suffix)
        n += 1

    log.info("Downloading '%s' -> %s ...", name, path)

    last_edit = [0.0]           # mutable, shared by progress closure
    last_pct = [-1]

    async def progress(current: int, done: int) -> None:
        nonlocal last_edit, last_pct
        pct = (current / done * 100) if done else 0
        now = time.monotonic()

        # Only edit when >0.5% progress AND >=700ms since last edit, or at 100%.
        changed = pct - last_pct[0] >= 0.5 or pct >= 100
        if changed and (now - last_edit[0] >= 0.7 or pct >= 100):
            bar = _progress_bar(pct)
            text = (
                f"⏳ Downloading `{name}`\n"
                f"`{bar}` **{pct:.0f}%**\n"
                f"{_fmt_size(current)} / {_fmt_size(done)}"
            )
            try:
                await status_msg.edit(text)
                last_edit[0] = now
                last_pct[0] = pct
            except Exception:  # noqa: BLE001 - edit race/limits; log & carry on
                log.debug("status edit skipped", exc_info=True)
        log.info("  -> %5.1f%%  (%s / %s)", pct, _fmt_size(current), _fmt_size(done))

    status = await client.download_media(
        event.message, file=str(path), progress_callback=progress
    )
    return str(status or path)


async def handler(event: events.NewMessage.Event) -> None:
    uid = event.from_id.user_id if event.from_id else None
    # "0" in the set = allow-anyone mode (empty list -> open too).
    if uid is not None and ALLOWED_USERS and 0 not in ALLOWED_USERS and uid not in ALLOWED_USERS:
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
        status_msg = await event.reply("Got it, downloading… ⏳")
        try:
            saved = await download_media(event, status_msg)
            size = Path(saved).stat().st_size / 1_048_576 if Path(saved).exists() else 0
            try:
                await status_msg.edit(
                    f"✅ Done — `{Path(saved).name}`\n"
                    f"`{saved}`\n"
                    f"({size:,.1f} MB)"
                )
            except Exception:  # noqa: BLE001 - keep going even if edit fails
                await event.reply(f"Done ✅ saved:\n`{saved}`\n({size:,.1f} MB)")
        except Exception as exc:  # noqa: BLE001
            log.exception("download failed")
            try:
                await status_msg.edit(f"Failed ❌ {exc}")
            except Exception:  # noqa: BLE001
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