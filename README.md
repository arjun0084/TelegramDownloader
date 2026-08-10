# Telegram Movie Downloader Bot
Forward a movie/file to **@beasboxplexbot** → it saves it to your media folder.

## Why this design
- **MTProto (Telethon)** session → **no 20 MB cloud limit**; 2 GB movies download fine.
- Ships as a **Docker container** — isolated, reproducible, you control the mount + env.
- No extra "Bot API server" process required.

## Files
| File | Purpose |
|------|---------|
| `downloader.py` | The bot itself |
| `Dockerfile` | Container image |
| `docker-compose.yml` | One-command deploy + volume mounts |
| `.env.example` | Secret template |
| `requirements.txt` | Runtime dep (telethon) |

---

## 🐳 Docker deploy (recommended) — run on the HOST where Docker + USB live

### 1. Get your API credentials (what you still need)
   - Go to **https://my.telegram.org/login** → log in (phone + code)
   - Click **API development tools**
   - Note `api_id` (number) and `api_hash` (string). Free, no installs.

### 2. Put this folder on the host
```bash
# copy /opt/data/tgdl to the host, e.g.:
scp -r hermes@<host>:/opt/data/tgdl /home/you/tgdl
cd /home/you/tgdl
```

### 3. Configure secrets
```bash
cp .env.example .env
nano .env     # paste TG_API_ID, TG_API_HASH  (token already filled)
```

### 4. Point the download volume at YOUR media path
Edit `docker-compose.yml`. Change ONLY the left side of this line
to where your media actually lives:
```yaml
volumes:
  - /media/devmon/sda1-usb-Kingston_DataTra:/downloads     # <- left side = YOUR host path
```

### 5. Build & run
```bash
docker compose up -d --build
docker compose logs -f     # watch it come online
```
The bot persists its session in a named volume (`tgdl_data`), so restarts
don't require re-login. `restart: unless-stopped` brings it back on reboot.

---

## 📲 Usage
- Open a private chat with **@beasboxplexbot**
- `/start` → it replies with the save path
- **Forward any movie/file** → downloads straight to the mounted folder.

## 🔐 Optional lockdown
Set `TG_ALLOWED_USER_ID` in `.env` to your numeric Telegram id
(get it from **@userinfobot**) so only you can use the bot. `0` = allow anyone.

---

## 🧪 Run WITHOUT Docker (native, host or here)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TG_API_ID=... TG_API_HASH=... TG_BOT_TOKEN=... \
       TG_OUTPUT_DIR=/media/devmon/sda1-usb-Kingston_DataTra
python downloader.py
```

---

## ⚠️ Note
Your **bot token is exposed in this Discord thread**. After you've deployed,
regenerate it via @BotFather and update `.env` — anyone who saw it can command
the bot until then.