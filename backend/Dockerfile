# Backend image for the AI Document Intelligence API.
# Includes the Tesseract (OCR) and Poppler (PDF rendering) system binaries that
# pytesseract / pdf2image need - these cannot be installed via pip.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching. Include the Postgres
# driver so DATABASE_URL can point at Supabase/Postgres in the cloud.
COPY requirements.txt .
RUN pip install -r requirements.txt "psycopg[binary]>=3.2"

COPY . .

# Uploaded files live here; mount a persistent volume at /data in production.
ENV STORAGE_DIR=/data/storage
RUN mkdir -p /data/storage

EXPOSE 8000

# $PORT is provided by most platforms (Render/Railway/Fly/Cloud Run).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
