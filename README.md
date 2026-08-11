# Telegram Movie Downloader Bot
Forward a movie/file to **@beasboxplexbot** → it saves it to your media folder.

🌐 **Landing page (GitHub Pages):** https://arjun0084.github.io/TelegramDownloader/

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
No repo clone or build needed — the image comes from Docker Hub.

### ⚡ One-command install (needs Docker + compose plugin)
```bash
curl -fsSL -o run.sh https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main/run.sh && bash run.sh
```
On first run it downloads `docker-compose.yml` + `.env.example`, creates `.env`,
and tells you to fill it in (secrets + `MEDIA_HOST_DIR`). Run `./run.sh` again and the
container is up. Updates are the same command.

> ℹ️ The curl URLs need the GitHub repo to be **Public** (raw files). If it's
> private, clone it instead or download via the GitHub web UI.

### 🚀 Even simpler for friends — plain `docker run`
No repo, no compose — just Docker and your credentials:
```bash
docker run -d --name tgdl --restart unless-stopped \
  -v /path/to/your/media:/downloads -v tgdl_data:/data \
  -e TG_API_ID=... -e TG_API_HASH=... -e TG_BOT_TOKEN=... \
  -e TG_OUTPUT_DIR=/downloads \
  arjun0084/telegram-downloader:latest
```

### 🔑 What you still need (one time)
- **API credentials**: https://my.telegram.org/login → **API development tools**
  → note `api_id` + `api_hash` (free, no installs).
- **Bot token**: already in `.env.example` (from @BotFather).
- **`MEDIA_HOST_DIR`**: full path to your downloads folder (in `.env`).

### 📝 Manual setup (if you prefer)
```bash
mkdir tgdl && cd tgdl
curl -fsSL -O https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main/docker-compose.yml
curl -fsSL -O https://raw.githubusercontent.com/arjun0084/TelegramDownloader/main/.env.example
cp .env.example .env
nano .env     # TG_API_ID, TG_API_HASH, MEDIA_HOST_DIR  (token already filled)
./run.sh
```

### ▶️ Day-to-day (once `.env` is filled)
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
