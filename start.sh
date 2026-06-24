#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Kill anything on these ports first
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

echo "Starting IdeaVault..."

# Backend
cd "$BACKEND"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Celery worker — pool=solo prevents fork() which kills Metal/MPS on macOS
.venv/bin/celery -A app.workers.celery_app worker --loglevel=info -Q generation --pool=solo --concurrency=1 &

# Frontend
cd "$FRONTEND"
npm run dev &

wait
