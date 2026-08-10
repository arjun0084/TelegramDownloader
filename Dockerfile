# Telegram Movie Downloader Bot — container image
# From: python:3.13-slim   (aarch64/arm64 and amd64 supported)
FROM python:3.13-slim

WORKDIR /app

# Install the single runtime dep (MTProto client, no size cap on downloads)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY downloader.py .

# Where media lands (expects a bind mount here from the host)
RUN mkdir -p /downloads

# The .session file Telethon writes (persist this via a volume too)
ENV TELEGRAM_SESSION=/data
RUN mkdir -p /data

# Config via env vars — DO NOT bake secrets into the image
ENV TG_API_ID=""
ENV TG_API_HASH=""
ENV TG_BOT_TOKEN=""
ENV TG_OUTPUT_DIR=/downloads
ENV TG_ALLOWED_USER_ID="0"

CMD ["python", "downloader.py"]