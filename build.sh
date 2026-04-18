#!/bin/bash
set -e

echo "==> Clearing Python cache..."
find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -not -path "./.venv/*" -delete 2>/dev/null || true

echo "==> Clearing disk cache..."
rm -rf /tmp/test-cache-enhancer

echo "==> Building Docker image (no cache)..."
docker build --no-cache -t code-enhancer .

echo "==> Running unit + integration tests..."
TESTING=true ENVIRONMENT=development CACHE_PATH=/tmp/test-cache-enhancer \
  .venv/bin/python -m pytest tests/ -v --timeout=30

echo ""
echo "All done. Service is ready to deploy."
