#!/bin/bash

echo "🚀 Starting Lead Autopilot Production Stack..."

# 1. Start Redis via Docker
echo "📦 Starting Redis container..."
docker rm -f redis-lead-autopilot 2>/dev/null || true
docker run -d -p 6379:6379 --name redis-lead-autopilot redis

# 2. Start Backend API
echo "⚙️ Starting FastAPI Backend on port 8000..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --port 8000 > ../backend.log 2>&1 &

# 3. Start Celery Worker
echo "👷 Starting Celery Worker..."
nohup celery -A celery_app worker --loglevel=info > ../celery.log 2>&1 &
cd ..

# 4. Start Frontend
echo "🎨 Starting React/Vite Frontend..."
cd frontend
npm install
nohup npm run dev > ../frontend.log 2>&1 &
cd ..

echo "✅ All services are starting up!"
echo "   - Frontend is available at http://localhost:5173"
echo "   - Backend API is available at http://localhost:8000"
echo "   - Logs are being written to backend.log, celery.log, and frontend.log"
