FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching —
# only re-runs pip install when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api/ ./api/

# Create cache directory — used by DiskCacheService at runtime
RUN mkdir -p /app/.cache

# Non-root user for security — never run as root in production
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/ping || exit 1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
