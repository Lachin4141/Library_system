# ── Backend Dockerfile ──────────────────────────────────────────────────────
# Place this file at:  backend/Dockerfile
#
# Build context is the `backend/` folder, so paths like ./app and ./requirements.txt
# are relative to backend/.
# ----------------------------------------------------------------------------

FROM python:3.12-slim

# Keep Python output unbuffered so logs appear instantly in `docker logs`
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first (layer is cached as long as requirements.txt doesn't change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Expose the port uvicorn will listen on
EXPOSE 8000

# Start the API.
# `--host 0.0.0.0` is required inside Docker so the port is reachable from outside.
# `--reload` is fine for development; remove it for production.
CMD ["uvicorn", "main:app", "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
