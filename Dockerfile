# ── Build stage: install dependencies ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (everything not excluded by .dockerignore)
COPY . .

# /data is the mount point for the persistent SQLite volume
RUN mkdir -p /data

EXPOSE 8501 8502

ENTRYPOINT ["python", "docker-entrypoint.py"]
