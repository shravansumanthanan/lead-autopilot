#!/usr/bin/env bash
# =============================================================================
# Lead Autopilot — Start All Services
# =============================================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$PROJECT_ROOT/backend"
FRONTEND="$PROJECT_ROOT/frontend"

# ─── Colours ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

echo ""
echo "  ██╗     ███████╗ █████╗ ██████╗      █████╗ ██╗   ██╗████████╗ ██████╗ "
echo "  ██║     ██╔════╝██╔══██╗██╔══██╗   ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗"
echo "  ██║     █████╗  ███████║██║  ██║   ███████║██║   ██║   ██║   ██║   ██║"
echo "  ██║     ██╔══╝  ██╔══██║██║  ██║   ██╔══██║██║   ██║   ██║   ██║   ██║"
echo "  ███████╗███████╗██║  ██║██████╔╝   ██║  ██║╚██████╔╝   ██║   ╚██████╔╝"
echo "  ╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝    ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ "
echo ""
info "Starting Lead Autopilot Production Stack..."
echo ""

# ─── Pre-flight checks ───────────────────────────────────────────────────────
[[ -f "$BACKEND/.env" ]] || die ".env file not found. Copy backend/.env.example to backend/.env and fill in your values."

OPENROUTER_KEY=$(grep "^OPENROUTER_API_KEY=" "$BACKEND/.env" | cut -d= -f2 | xargs)
if [[ -z "$OPENROUTER_KEY" || "$OPENROUTER_KEY" == "sk-or-v1-your-key-here" ]]; then
    warn "OPENROUTER_API_KEY is not set in backend/.env — AI analysis will use fallback templates."
fi

# ─── 1. Redis ─────────────────────────────────────────────────────────────────
info "Starting Redis..."
if command -v redis-cli &>/dev/null && redis-cli ping &>/dev/null 2>&1; then
    success "Redis already running."
elif command -v brew &>/dev/null; then
    brew services start redis &>/dev/null
    sleep 1
    redis-cli ping &>/dev/null && success "Redis started via Homebrew." || die "Redis failed to start."
elif command -v docker &>/dev/null; then
    docker rm -f redis-lead-autopilot 2>/dev/null || true
    docker run -d -p 6379:6379 --name redis-lead-autopilot redis:alpine &>/dev/null
    sleep 2
    success "Redis started via Docker."
else
    die "Redis not found. Install with: brew install redis  OR  apt install redis-server"
fi

# ─── 2. Python virtualenv ─────────────────────────────────────────────────────
if [[ -f "$BACKEND/venv/bin/activate" ]]; then
    VENV="$BACKEND/venv"
elif [[ -f "$BACKEND/.venv/bin/activate" ]]; then
    VENV="$BACKEND/.venv"
else
    warn "No virtualenv found. Creating one..."
    python3 -m venv "$BACKEND/venv"
    VENV="$BACKEND/venv"
fi
source "$VENV/bin/activate"
info "Using virtualenv: $VENV"

# Install dependencies if needed
if ! python -c "import fastapi" &>/dev/null 2>&1; then
    info "Installing backend dependencies..."
    pip install -q -r "$BACKEND/requirements.txt"
fi

# ─── 3. FastAPI Backend ───────────────────────────────────────────────────────
info "Starting FastAPI backend on :8000..."
(cd "$BACKEND" && nohup uvicorn main:app --host 0.0.0.0 --port 8000 > "$PROJECT_ROOT/backend.log" 2>&1 &)
sleep 2

if curl -s http://localhost:8000/api/health &>/dev/null; then
    success "Backend running at http://localhost:8000"
else
    warn "Backend may still be starting. Check backend.log if issues arise."
fi

# ─── 4. Celery Worker ─────────────────────────────────────────────────────────
info "Starting Celery worker..."
(cd "$BACKEND" && nohup celery -A celery_app worker --loglevel=info --concurrency=2 > "$PROJECT_ROOT/celery.log" 2>&1 &)
sleep 2
success "Celery worker running"

# ─── 5. Frontend ──────────────────────────────────────────────────────────────
info "Starting Next.js frontend on :5173..."
if [[ ! -d "$FRONTEND/node_modules" ]]; then
    info "Installing frontend dependencies..."
    (cd "$FRONTEND" && npm install --silent)
fi
(cd "$FRONTEND" && nohup npm run dev -- -p 5173 > "$PROJECT_ROOT/frontend.log" 2>&1 &)
sleep 3
success "Frontend running at http://localhost:5173"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All services started successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  📝 Frontend     →  ${BLUE}http://localhost:5173${NC}"
echo -e "  ⚡ Backend API  →  ${BLUE}http://localhost:8000${NC}"
echo -e "  📖 API Docs     →  ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Logs: backend.log | celery.log | frontend.log"
echo ""
