FROM node:20-alpine AS nextjs-builder

WORKDIR /app

# Copy package files and install deps
COPY webui/nextjs-chat/package*.json ./
RUN npm ci --force || npm install --force

# Copy Next.js source and build static export
COPY webui/nextjs-chat/ ./
RUN npm run build && npm run build:static || npm run build:static || true

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# (Ollama は別サービスを推奨。OKAMI コンテナ内にはインストールしない)

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding webui build outputs)
COPY . .

# Copy Next.js build output into serving directory
COPY --from=nextjs-builder /app/out /app/webui/static

# Ensure UI directory exists and verify builder output is present
# Cache bust: 2025-09-13-02:30
RUN mkdir -p /app/webui/static \
 && ls -la /app/webui/static/ \
 && test -f /app/webui/static/index.html

# Create necessary directories
RUN mkdir -p /app/storage /app/logs /app/knowledge

# Make wait script executable
RUN chmod +x /app/scripts/wait-for-services.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CREWAI_STORAGE_DIR=/app/storage

# Expose ports
EXPOSE 8000

# Health check (respect dynamic PORT; default to 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD sh -lc 'curl -f http://localhost:${PORT:-8000}/health || exit 1'

# Run the application (bind to PORT; no reload in production)
CMD ["sh", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
