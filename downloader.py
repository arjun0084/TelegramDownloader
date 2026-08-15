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
from collections import defaultdict

from telethon import TelegramClient, events
from telethon.tl.custom import Button

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

# Maximum number of parallel downloads (0 = unlimited)
try:
    MAX_PARALLEL = int(os.environ.get("TG_MAX_PARALLEL", "2"))
except ValueError:
    MAX_PARALLEL = 2
if MAX_PARALLEL > 0:
    DOWNLOAD_SEMAPHORE = asyncio.Semaphore(MAX_PARALLEL)
else:
    DOWNLOAD_SEMAPHORE = None  # unlimited

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("tgdl")

# Per-message download state: key = (chat_id, message_id)
# value = dict with start_time, last_bytes, last_time, cancelled
_download_state = defaultdict(lambda: {"start_time": 0.0, "last_bytes": 0, "last_time": 0.0, "cancelled": False})
# Track active download tasks to await on shutdown
_active_tasks = set()

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
    # Limit concurrency via semaphore if configured
    if DOWNLOAD_SEMAPHORE is not None:
        async with DOWNLOAD_SEMAPHORE:
            return await _download_media_inner(event, status_msg)
    else:
        return await _download_media_inner(event, status_msg)

async def _download_media_inner(event: events.NewMessage.Event, status_msg) -> str:
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

    # Init state for this message
    chat_id = event.chat_id
    msg_id = event.message.id
    state = _download_state[(chat_id, msg_id)]
    state["start_time"] = time.monotonic()
    state["last_bytes"] = 0
    state["last_time"] = state["start_time"]
    state["cancelled"] = False

    async def progress(current: int, total: int) -> None:
        """Progress callback with speed calculation and cancel support."""
        if state["cancelled"]:
            raise Exception("Download cancelled by user")
        now = time.monotonic()
        elapsed = now - state["last_time"]
        if elapsed >= 0.5:  # update speed at most twice per second
            bytes_since = current - state["last_bytes"]
            speed_bps = bytes_since / elapsed if elapsed > 0 else 0
            state["last_bytes"] = current
            state["last_time"] = now
        else:
            speed_bps = 0.0

        pct = (current / total * 100) if total else 0
        # Only edit when >0.5% progress AND >=700ms since last edit, or at 100%.
        changed = pct - state.get("_last_pct", -1) >= 0.5 or pct >= 100
        last_edit_time = state.get("_last_edit", 0.0)
        if changed and (now - last_edit_time >= 0.7 or pct >= 100):
            bar = _progress_bar(pct)
            speed_str = _fmt_size(int(speed_bps)) + "/s" if speed_bps else ""
            text = (
                f"⏳ Downloading `{name}`\n"
                f"`{_progress_bar(pct)}` **{pct:.0f}%** {speed_str}\n"
                f"{_fmt_size(current)} / {_fmt_size(total)}"
            )
            try:
                await status_msg.edit(text)
                state["_last_edit"] = now
                state["_last_pct"] = pct
            except Exception:  # noqa: BLE001 - edit race/limits; log & carry on
                log.debug("status edit skipped", exc_info=True)
        log.info("  -> %5.1f%%  (%s / %s)  speed: %s/s", pct, _fmt_size(current), _fmt_size(total), _fmt_size(int(speed_bps)) if speed_bps else "0 B/s")

    try:
        status = await client.download_media(
            event.message, file=str(path), progress_callback=progress
        )
    except Exception as exc:
        # If cancelled, we raise generic Exception above; treat as cancelled.
        if "cancelled" in str(exc).lower():
            log.info("Download cancelled by user for %s", name)
            try:
                await status_msg.edit(f"🛑 Cancelled — `{name}`")
            except Exception:
                pass
            # Clean up state
            _download_state.pop((chat_id, msg_id), None)
            raise  # re-raise to be caught by outer handler if needed
        else:
            raise

    # Clean up state on success
    _download_state.pop((chat_id, msg_id), None)
    return str(status or path)


async def handler(event: events.NewMessage.Event) -> None:
    # Defensive: never react to our own outgoing messages (loop guard).
    if event.out:
        return

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
        # Send initial message with cancel button
        buttons = [[Button.callback("🛑 Cancel", f"cancel:{event.chat_id}:{event.message.id}")]]
        status_msg = await event.reply("Got it, downloading… ⏳", buttons=buttons)
        # Fire-and-forget the download task
        task = asyncio.create_task(download_media(event, status_msg))
        _active_tasks.add(task)
        task.add_done_callback(_active_tasks.discard)
        try:
            await task
        except Exception as exc:
            # Already handled inside download_media (cancelled or failed)
            pass
    else:
        await event.reply("Send or forward a media file (video/document/photo).")


# ------------------------------------------------------------------------
# Callback query handler for cancel button
# ------------------------------------------------------------------------
async def callback_handler(event: events.CallbackQuery.Event) -> None:
    data = event.data.decode()
    if not data.startswith("cancel:"):
        await event.answer("Unknown action", alert=True)
        return
    try:
        _, chat_id_str, msg_id_str = data.split(":")
        chat_id = int(chat_id_str)
        msg_id = int(msg_id_str)
    except Exception:
        await event.answer("Invalid request", alert=True)
        return

    # Verify it's the same user who started the download (optional but good)
    if event.sender_id and event.sender_id != event.original_update.user_id:
        await event.answer("Not your download", alert=True)
        return

    state = _download_state.get((chat_id, msg_id))
    if not state:
        await event.answer("No active download to cancel", alert=True)
        return

    state["cancelled"] = True
    await event.answer("Cancelling…", alert=False)
    # The download_media progress loop will notice and abort.


async def main() -> None:
    global client
    if API_ID == 0 or not API_HASH or not BOT_TOKEN:
        raise SystemExit(
            "Missing config. Set TG_API_ID, TG_API_HASH, TG_BOT_TOKEN (and TG_OUTPUT_DIR)."
        )
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    # Ignore the bot's own outgoing messages (else its replies re-trigger the
    # handler and loop "Not authorised"). Forwards are still handled — that's
    # the whole point (e.forward must NOT be excluded).
    client.on(events.NewMessage(func=lambda e: e.is_private and not e.out))(handler)
    client.on(events.CallbackQuery)(callback_handler)
    await client.start(bot_token=BOT_TOKEN)
    me = await client.get_me()
    log.info("Bot online as %s. Waiting for forwarded files ...", me.username)
    log.info("Output dir: %s", OUTPUT_DIR)
    await client.run_until_disconnected()
    # Wait for any remaining download tasks to finish (or be cancelled)
    if _active_tasks:
        await asyncio.wait(_active_tasks, timeout=5.0)


if __name__ == "__main__":
    asyncio.run(main())