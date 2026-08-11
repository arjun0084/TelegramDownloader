# Telegram Movie Downloader Bot
Forward a movie/file to **@beasboxplexbot** → it saves it to your media folder.

## Why this design
- **MTProto (Telethon)** session → **no 20 MB cloud limit**; 2 GB movies download fine.
- Ships as a **Docker container** pulled from **Docker Hub** — no cloning/building.
- No extra "Bot API server" process required.
- CI (GitHub Actions) builds the multi-arch image (`amd64` + `arm64`) and pushes it to Docker Hub.

## Files
| File | Purpose |
|------|---------|
| `downloader.py` | The bot itself |
| `Dockerfile` | Container image (built by CI) |
| `docker-compose.yml` | One-command deploy + volume mounts (uses the Hub image) |
| `run.sh` | Thin `docker compose` wrapper: install/update/logs/… |
| `.github/workflows/docker-hub.yml` | CI: build + push image to Docker Hub |
| `.env.example` | Secret template |
| `requirements.txt` | Runtime dep (telethon) |

---

## 🐳 Deploy (recommended) — run on the HOST where Docker + USB live
No repo clone needed for friends: just `docker compose` + `.env`.

### 1. Get your API credentials
   - Go to **https://my.telegram.org/login** → log in (phone + code)
   - Click **API development tools**
   - Note `api_id` (number) and `api_hash` (string). Free, no installs.

### 2. Get the compose file + config
```bash
mkdir tgdl && cd tgdl
curl -O https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main/.env.example
cp .env.example .env
nano .env     # paste TG_API_ID, TG_API_HASH  (token already filled)
```

### 3. Point the download volume at YOUR media path
Edit `docker-compose.yml`. Change ONLY the left side of this line
to where your media actually lives:
```yaml
volumes:
  - /media/devmon/sda1-usb-Kingston_DataTra:/downloads     # <- left side = YOUR host path
```

### 4. Run (pulls the image from Docker Hub)
```bash
./run.sh            # install: pull + start        (or: docker compose up -d)
./run.sh update     # pull latest image + recreate (updates are this easy)
./run.sh logs       # follow logs
```
The bot persists its session in a named volume (`tgdl_data`), so restarts
don't require re-login. `restart: unless-stopped` brings it back on reboot.

---

## 📲 Usage
- Open a private chat with **@beasboxplexbot**
- `/start` → it replies with the save path
- **Forward any movie/file** → the same message shows a live progress bar,
  then flips to `✅ Done` when saved to the mounted folder.

## 🔐 Optional lockdown
Set `TG_ALLOWED_USER_ID` in `.env` to the numeric Telegram ids allowed to use it.
Comma-separate for multiple users, e.g. `TG_ALLOWED_USER_ID=11111,22222`.
Get your id from **@userinfobot**. `0` (default) = allow anyone private chat.

---

## 🤖 CI: automatic Docker Hub builds
`.github/workflows/docker-hub.yml` builds and pushes on every `main` commit:
- tags pushed → `arjun0084/telegram-downloader:latest` + `:<version>`
- branch pushes → `:latest` + `:sha-<commit>`
- manual run possible from the Actions tab

**One-time setup** (in the GitHub repo → Settings → Secrets and variables → Actions):
- `DOCKERHUB_USERNAME` → `arjun0084`
- `DOCKERHUB_TOKEN` → Docker Hub access token (Read/Write/Delete) from
  https://hub.docker.com/settings/security

The Docker Hub repo must exist and be **Public**:
https://hub.docker.com/repository/create → name `telegram-downloader`.

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
Your **bot token was exposed in a chat thread**. After you've deployed,
regenerate it via @BotFather and update `.env` — anyone who saw it can command
the bot until then.
