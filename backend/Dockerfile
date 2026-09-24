# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Backend Dockerfile — FastAPI + Motor + Couchbase SDK
# ---------------------------------------------------------------------------
FROM python:3.11.15-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps required by couchbase SDK (libev, openssl) and typical Python wheels.
# build-essential is only needed if a wheel is unavailable; kept lean otherwise.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir \
        "emergentintegrations" \
        --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Copy application source
COPY . /app

# Create non-root user + writable uploads dir
RUN useradd --no-create-home --uid 10001 appuser \
 && mkdir -p /var/lib/parking/uploads \
 && chown -R appuser:appuser /app /var/lib/parking
USER appuser

ENV UPLOAD_DIR=/var/lib/parking/uploads \
    PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
