FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-calc \
    ffmpeg \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Security: Pillow 12.3+ fixes 35 CVEs. moviepy 2.2.1 still pins pillow<12 in metadata but works
# with 12.x (verified: MP4->MP3, WAV->MP3, MP3->MP4). --no-deps skips the resolver conflict.
RUN pip install --no-cache-dir --no-deps "Pillow==12.3.0"

COPY . .

EXPOSE $PORT
CMD uvicorn server:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
