# Lead Autopilot

An end-to-end automated lead intelligence platform. When a prospect submits a form, the system autonomously scrapes their company website, runs AI-powered analysis, generates a personalized PDF report, and emails it — all without human intervention.

---

## System Architecture

```
Prospect submits form
        │
        ▼
┌─────────────────┐     HTTP POST      ┌──────────────────────┐
│   Next.js UI    │ ─────────────────► │  FastAPI Backend      │
│  (port 5173)    │                    │  (port 8000)          │
└─────────────────┘                    └──────────┬───────────┘
                                                  │ enqueues task
                                                  ▼
                                       ┌──────────────────────┐
                                       │   Celery Worker      │
                                       │   (Redis broker)     │
                                       └──────────┬───────────┘
                                                  │
                          ┌───────────────────────┼────────────────────────┐
                          ▼                       ▼                        ▼
                 ┌────────────────┐   ┌──────────────────┐   ┌────────────────────┐
                 │  Web Scraper   │   │  OpenRouter AI   │   │  PDF Generator     │
                 │  (httpx + BS4) │   │  (Qwen model)    │   │  (Jinja2+WeasyPrint│
                 └────────────────┘   └──────────────────┘   └────────────────────┘
                          │                       │                        │
                          └───────────────────────┼────────────────────────┘
                                                  ▼
                                       ┌──────────────────────┐
                                       │  Email + Bonus       │
                                       │  Google Sheets/Drive │
                                       └──────────────────────┘
```

### Pipeline Steps

| Step | Description |
|------|-------------|
| **1. Validate** | Pydantic validates and sanitises all form inputs |
| **2. Scrape** | Multi-tier scraper: Firecrawl → httpx/BeautifulSoup → Metadata fallback |
| **3. Enrich** | Optional Serper.dev Google search adds public context |
| **4. Analyse** | OpenRouter Qwen AI generates SWOT, scorecard, roadmap, and key findings |
| **5. Generate PDF** | Jinja2 HTML template rendered to a multi-page PDF by WeasyPrint |
| **6. Email** | PDF attached to a branded HTML email sent via Gmail SMTP |
| **7. Log** | Lead logged to Google Sheets (optional) and PDF archived to Google Drive (optional) |

### Resilience Design

- **Circuit breaker** on AI and scraping calls — prevents cascading failures
- **Retry with exponential backoff** on transient network errors
- **Timeout guards** (30s scraping, 45s AI) — no hung workers
- **Graceful degradation**: if Firecrawl fails → basic scraper; if AI fails → industry template fallback
- **Quality scoring** (0.0–1.0) and confidence levels (High / Medium / Low) reported per-lead

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (installed via `brew install redis` or Docker)
- An [OpenRouter](https://openrouter.ai) API key
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords)

### 1. Clone and configure

```bash
git clone <repo-url>
cd lead-autopilot

cp backend/.env.example backend/.env
# Edit backend/.env — at minimum set OPENROUTER_API_KEY, SMTP_EMAIL, SMTP_PASSWORD
```

### 2. Set up the Python environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
```

### 3. Set up the frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Start everything

```bash
chmod +x start_all.sh
./start_all.sh
```

Open **http://localhost:5173** — submit a form and watch the pipeline run.

---

## Configuration

All configuration lives in **`backend/.env`**. Copy from `.env.example`:

```env
# ── Required ──────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-v1-...       # Get from openrouter.ai
OPENROUTER_MODEL=qwen/qwen3-235b-a22b  # Or any other OpenRouter model

SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_EMAIL=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx     # Gmail App Password (not your login password)
SENDER_NAME=Your Name

# ── Business Branding (shown on PDF cover) ────────────
BUSINESS_NAME=Your Company
BUSINESS_TAGLINE=Data-Driven Growth
BUSINESS_WEBSITE=https://yourcompany.com
BUSINESS_EMAIL=contact@yourcompany.com
BUSINESS_PHONE=+1 555 123 4567

# ── Optional: Richer Scraping ─────────────────────────
# FIRECRAWL_API_KEY=fc-...            # firecrawl.dev — handles JS-rendered sites

# ── Optional: Web Search Context ─────────────────────
# SERPER_API_KEY=...                  # serper.dev — Google search enrichment

# ── Optional: Google Sheets (Bonus) ──────────────────
# GOOGLE_SHEETS_CREDENTIALS_FILE=service_account.json
# GOOGLE_SHEET_NAME=Lead Autopilot Tracker

# ── Optional: Google Drive (Bonus) ────────────────────
# GOOGLE_DRIVE_CREDENTIALS_FILE=service_account.json
# GOOGLE_DRIVE_FOLDER_ID=your-folder-id
```

### Gmail App Password Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to **Google Account → Security → 2-Step Verification → App passwords**
3. Create a new app password (select "Mail" + your device)
4. Use the 16-character code as `SMTP_PASSWORD` in `.env`

---

## Project Structure

```
lead-autopilot/
├── backend/
│   ├── main.py                   # FastAPI app and API routes
│   ├── tasks.py                  # Celery task — orchestrates the full pipeline
│   ├── celery_app.py             # Celery + Redis configuration
│   ├── database.py               # SQLAlchemy models and DB session
│   ├── core_models.py            # Pydantic data schemas (shared source of truth)
│   ├── requirements.txt
│   ├── .env.example              # Template for environment variables
│   │
│   ├── workflows/
│   │   └── report_pipeline.py    # Enrichment orchestration (scrape → search → AI → score)
│   │
│   ├── services/
│   │   ├── scraper.py            # httpx + BeautifulSoup website scraper
│   │   ├── resilient_scraper.py  # Scraper with circuit breaker + fallbacks
│   │   ├── firecrawl_scraper.py  # Firecrawl API integration (optional)
│   │   ├── metadata_scraper.py   # Lightweight metadata-only fallback
│   │   ├── web_search.py         # Serper.dev Google search enrichment
│   │   ├── ai_analysis.py        # OpenRouter AI prompt + parsing
│   │   ├── resilient_ai_analysis.py  # AI with circuit breaker + fallback
│   │   ├── fallback_generator.py # Industry-template fallback when AI fails
│   │   ├── quality_scorer.py     # 0.0–1.0 data quality scoring
│   │   ├── confidence_assigner.py
│   │   ├── content_validator.py  # Hallucination / repetition detection
│   │   ├── error_categorizer.py  # Error classification for observability
│   │   ├── pdf_generator.py      # Jinja2 → WeasyPrint PDF pipeline
│   │   ├── email_service.py      # Gmail SMTP with HTML template + retry
│   │   └── templates/
│   │       └── report.html       # Jinja2 PDF report template (5 pages)
│   │
│   ├── integrations/
│   │   ├── sheets.py             # Google Sheets logging (bonus)
│   │   ├── drive.py              # Google Drive PDF archival (bonus)
│   │   └── webhooks.py           # Slack + CRM webhook notifications
│   │
│   └── utils/
│       ├── circuit_breaker.py    # Generic async circuit breaker
│       ├── retry.py              # Exponential-backoff decorator
│       ├── timeout.py            # Async timeout decorator
│       └── validation.py         # URL normalisation + schema helpers
│
├── frontend/
│   └── src/app/
│       └── page.tsx              # Single-page Next.js app (form → live progress → PDF)
│
├── output/                       # Generated PDFs saved here
├── start_all.sh                  # One-command startup script
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Service status and integration flags |
| `POST` | `/api/leads` | Submit a new lead (returns `lead_id`) |
| `GET` | `/api/leads/{id}/status` | Poll pipeline status |
| `GET` | `/api/leads/{id}/pdf` | Download the generated PDF report |

Interactive docs available at **http://localhost:8000/docs**

### Submit a Lead (cURL)

```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "jane@acme.com",
    "company": "Acme Corp",
    "website": "https://acme.com",
    "industry": "SaaS",
    "company_size": "50-200",
    "message": "Struggling with customer retention and onboarding drop-off."
  }'
```

Response:
```json
{ "lead_id": "a3f1b2c4", "status": "submitted", "message": "Processing has begun." }
```

### Poll Status

```bash
curl http://localhost:8000/api/leads/a3f1b2c4/status
```

```json
{
  "lead_id": "a3f1b2c4",
  "current_step": "enriching",
  "steps_completed": ["submitted", "validating"],
  "is_complete": false
}
```

---

## Bonus Features

### Google Sheets Lead Tracker

Automatically appends each lead's name, email, company, timestamp, and report status to a Google Sheet.

Setup:
1. Create a Google Cloud project and enable the Sheets API
2. Create a service account and download `service_account.json`
3. Share your Google Sheet with the service account email
4. Set `GOOGLE_SHEETS_CREDENTIALS_FILE=service_account.json` in `.env`

### Google Drive PDF Archival

Saves a copy of each generated PDF to a specified Drive folder.

Setup:
1. Enable the Drive API in your Google Cloud project
2. Same service account as Sheets (or a new one)
3. Share the Drive folder with the service account
4. Set `GOOGLE_DRIVE_CREDENTIALS_FILE` and `GOOGLE_DRIVE_FOLDER_ID` in `.env`

---

## How the PDF Report Is Structured

The generated PDF is a 5–6 page A4 document:

| Page | Content |
|------|---------|
| **Cover** | Company name, industry, date, quality score, brand colours |
| **Overview** | Website intelligence, services, tech stack |
| **Executive Summary** | AI-written strategic summary + Digital Scorecard |
| **SWOT Analysis** | Full 4-quadrant SWOT + risk areas + strategic opportunities |
| **Key Findings** | Category-observation table from AI analysis |
| **Action Roadmap** | Immediate / 30-day / 90-day prioritised recommendations |

The colour theme is automatically selected based on industry (tech = indigo, finance = emerald, healthcare = teal, etc.).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `401 Unauthorized` from OpenRouter | Your API key is wrong or missing in `backend/.env` |
| `SMTP authentication failed` | Use a Gmail App Password, not your login password |
| `No module named X` | Run `pip install -r requirements.txt` inside the venv |
| Celery not processing | Ensure Redis is running: `redis-cli ping` |
| PDF not generating | Check `celery.log` for WeasyPrint errors |
| Frontend can't reach backend | Ensure backend is on port 8000 and CORS is enabled |

---

*Built with FastAPI · Celery · Redis · OpenRouter (Qwen) · WeasyPrint · Next.js*
