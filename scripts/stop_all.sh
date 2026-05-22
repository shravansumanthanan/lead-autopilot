#!/usr/bin/env bash
# =============================================================================
# Lead Autopilot — Stop All Services
# =============================================================================

echo "Stopping Lead Autopilot services..."

# Kill Celery worker
pkill -f "celery -A celery_app worker" && echo "Celery worker stopped." || echo "Celery worker not running."

# Kill FastAPI backend
pkill -f "uvicorn main:app" && echo "FastAPI backend stopped." || echo "FastAPI backend not running."

# Kill Next.js frontend
pkill -f "next" && echo "Next.js frontend stopped." || echo "Next.js frontend not running."

# Stop Redis if running via Docker
if command -v docker &>/dev/null; then
    docker rm -f redis-lead-autopilot 2>/dev/null && echo "Docker Redis stopped." || true
fi

echo "All services stopped."
