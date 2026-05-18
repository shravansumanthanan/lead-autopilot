#!/bin/bash
# Lead Autopilot — Quick Setup Script
# Run this once to set up your development environment.

set -e

echo ""
echo "⚡ Lead Autopilot — Setup"
echo "========================="
echo ""

# ── Check dependencies ───────────────────────────────────────
echo "→ Checking system dependencies..."

if ! command -v python3.13 &>/dev/null && ! command -v python3.12 &>/dev/null && ! command -v python3.11 &>/dev/null; then
  echo "  ✗ Python 3.11+ not found. Install via: brew install python@3.13"
  exit 1
fi

PYTHON=$(command -v python3.13 || command -v python3.12 || command -v python3.11)
echo "  ✓ Python: $PYTHON"

if ! command -v node &>/dev/null; then
  echo "  ✗ Node.js not found. Install via: brew install node"
  exit 1
fi
echo "  ✓ Node.js: $(node --version)"

# ── WeasyPrint system deps (macOS) ───────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo ""
  echo "→ Checking WeasyPrint system libraries (macOS)..."
  if ! brew list pango &>/dev/null 2>&1; then
    echo "  Installing pango, cairo, libffi, gdk-pixbuf..."
    brew install pango cairo libffi gdk-pixbuf
  else
    echo "  ✓ Pango/Cairo already installed"
  fi
fi

# ── Backend setup ─────────────────────────────────────────────
echo ""
echo "→ Setting up Python backend..."

cd backend
$PYTHON -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "  ✓ Python dependencies installed"

# Copy env file if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ✓ Created backend/.env from template"
  echo ""
  echo "  ⚠️  ACTION REQUIRED: Edit backend/.env and fill in:"
  echo "      OPENROUTER_API_KEY — get free key at openrouter.ai"
  echo "      SMTP_EMAIL + SMTP_PASSWORD — Gmail App Password"
  echo "      BUSINESS_NAME, BUSINESS_EMAIL — your branding"
fi

deactivate
cd ..

# ── Frontend setup ────────────────────────────────────────────
echo ""
echo "→ Setting up frontend..."
cd frontend
npm install --silent
echo "  ✓ Node dependencies installed"
cd ..

# ── Output directory ──────────────────────────────────────────
mkdir -p output
echo ""
echo "✅ Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NEXT STEPS:"
echo ""
echo "  1. Edit backend/.env with your API keys"
echo ""
echo "  2. Start the backend (Terminal 1):"
echo "     cd backend && source venv/bin/activate"
echo "     uvicorn main:app --reload --port 8000"
echo ""
echo "  3. Start the frontend (Terminal 2):"
echo "     cd frontend && npm run dev"
echo ""
echo "  4. Open http://localhost:5173 in your browser"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
