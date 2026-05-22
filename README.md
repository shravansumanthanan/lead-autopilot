<div align="center">

  <h1>Lead Autopilot</h1>
  <p><strong>Enterprise-Grade Automated Business Intelligence & Lead Enrichment</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/Celery-5.4-37814A?logo=celery&logoColor=white" alt="Celery">
    <img src="https://img.shields.io/badge/Next.js-18%2B-black?logo=next.js&logoColor=white" alt="Next.js">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  </p>

  <p>
    <a href="#architecture">Architecture</a> •
    <a href="#core-features">Features</a> •
    <a href="#resilience-engineering">Resilience</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#api-reference">API</a> •
    <a href="#development">Development</a>
  </p>

</div>

---

## 📖 Overview

**Lead Autopilot** is an automated, AI-driven lead enrichment pipeline that transforms raw business prospect data into highly actionable, 5-page PDF intelligence reports — delivered directly to the prospect's inbox.

Built with Python (FastAPI + Celery) and Next.js, it employs a 5-layer enterprise architecture with multi-tier scraping fallbacks, circuit breakers, and hallucination detection to guarantee pipeline continuity in production environments.

---

## 🏗️ Architecture

Lead Autopilot follows a strict separation of concerns, decoupling the HTTP layer from business logic and external integrations.

```mermaid
graph TD
    %% Frontend
    User([User Form]) -->|Next.js| API[FastAPI Gateway]

    %% API & Queue
    API --> DB[(SQLite / PostgreSQL)]
    API -->|Enqueue Task| Redis[(Redis Broker)]
    Redis --> Worker[Celery Worker]

    %% Worker Pipeline
    Worker --> Pipeline{Enrichment Pipeline}

    %% Pipeline Steps
    Pipeline --> Scraper[Resilient Scraper]
    Pipeline --> Analyzer[AI Analyzer]
    Pipeline --> PDF[PDF Generator]

    %% External Integrations
    Scraper -.->|HTTP/Firecrawl| TargetWeb(Target Website)
    Analyzer -.->|OpenRouter API| LLM(LLM Engine)

    %% Delivery
    PDF --> Delivery[Delivery Engine]
    Delivery --> SMTP[Email Dispatch]
    Delivery --> Webhook[Slack / CRM Webhooks]
```

**Request lifecycle:**
1. User submits a lead form → FastAPI writes a record to the DB and enqueues a Celery task (returns `202` immediately)
2. Celery worker scrapes the company website, runs AI analysis, and generates a PDF
3. PDF is emailed to the prospect; Slack/CRM webhooks fire asynchronously
4. Client polls `/api/leads/{id}/status` until `is_complete: true`

---

## ✨ Core Features

* **Intelligent Web Extraction** — Bypasses anti-scraping walls via a 3-tier fallback engine (Firecrawl API → httpx/BS4 → Metadata-only).
* **AI Business Analysis** — Uses OpenRouter (Qwen/LLaMA) to generate SWOT analyses, digital maturity scorecards, and actionable roadmaps.
* **Resilience Engineering** — Hand-rolled Circuit Breakers and Exponential Backoff engines protect all external API calls.
* **Hallucination Detection** — Content validators strictly ensure AI responses meet length, uniqueness, and structural Pydantic bounds.
* **Automated PDF Delivery** — Jinja2 & WeasyPrint compile rich HTML templates into personalized executive PDF briefs.
* **Async Webhooks** — Non-blocking Celery workers dispatch notifications to Slack and push data to CRM/Google Sheets via `asyncio.to_thread()`.

---

## 🛡️ Resilience Engineering

This system was designed for the chaos of the open internet. It treats external failures as expected states rather than edge cases.

1. **Circuit Breakers** — If OpenRouter or Firecrawl fail 3 times consecutively, the breaker opens. Subsequent leads immediately fail over to structured industry-template fallbacks, preventing cascading queue timeouts.
2. **Quality Scoring** — A composite scoring engine rates intelligence output (0.0–1.0) and assigns a Confidence Level (High / Medium / Low) to every report.
3. **Pydantic Hardening** — All AI outputs are forced through strict schema validators. If the LLM returns unstructured text, a secondary rescue parser attempts to extract JSON.
4. **PDF Fallback** — If WeasyPrint rendering fails (e.g., missing system libraries), the pipeline degrades gracefully to a clean Markdown report rather than erroring out.

---

## 🚀 Quick Start

### Prerequisites

| Dependency | Min Version | Install |
|---|---|---|
| Python | 3.11+ | `brew install python@3.13` |
| Node.js | 18+ | `brew install node` |
| Redis | 7+ | `brew install redis && brew services start redis` |

### 1. Clone & Install

```bash
git clone https://github.com/shravansumanthanan/lead-autopilot.git
cd lead-autopilot

# Creates venvs, installs pip and npm dependencies, copies env template
./scripts/setup.sh
```

### 2. Configure

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and set your credentials. **Only `OPENROUTER_API_KEY` is required** to test the core pipeline. All other integrations (email, Google Sheets, Slack) are optional and skip gracefully when unconfigured.

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-...

# Development default — switch to PostgreSQL for multi-worker production
DATABASE_URL=sqlite:///./leads.db
```

### 3. Start

You can start the entire stack using our quick-launch script:

```bash
./scripts/start_all.sh
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API Docs | http://localhost:8000/docs |

#### Running Services Individually (Recommended for Debugging)

If you prefer to run services in separate terminals to monitor logs individually:

**Terminal 1: Start Redis Broker**
```bash
brew services start redis
```

**Terminal 2: Start Python Backend API (FastAPI)**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 3: Start Celery Worker Pipeline**
```bash
cd backend
source venv/bin/activate
celery -A celery_app worker --loglevel=info
```

**Terminal 4: Start Frontend Dev Server (Next.js)**
```bash
cd frontend
npm run dev
```

---

## 📂 Project Structure

```text
lead-autopilot/
├── backend/
│   ├── main.py                    # FastAPI app, routes, lifespan
│   ├── database.py                # SQLAlchemy models, engine config (SQLite / PostgreSQL)
│   ├── core_models.py             # Centralized Pydantic schemas & enums
│   ├── tasks.py                   # Celery task definitions & pipeline orchestration
│   ├── celery_app.py              # Celery + Redis broker configuration
│   │
│   ├── workflows/
│   │   └── report_pipeline.py     # Top-level enrichment orchestrator
│   │
│   ├── services/                  # Core business logic
│   │   ├── resilient_scraper.py   # 3-tier scraping with circuit breakers & retries
│   │   ├── scraper.py             # httpx + BeautifulSoup full-page scraper
│   │   ├── firecrawl_scraper.py   # Firecrawl API integration (JS-rendered pages)
│   │   ├── metadata_scraper.py    # Lightweight metadata-only fallback scraper
│   │   ├── resilient_ai_analysis.py  # AI service with CB, retries, hallucination check
│   │   ├── ai_analysis.py         # OpenRouter prompt builder & JSON parser
│   │   ├── fallback_generator.py  # Industry template fallbacks when AI fails
│   │   ├── content_validator.py   # Repetition/hallucination loop detector
│   │   ├── quality_scorer.py      # Composite 0.0–1.0 data quality scorer
│   │   ├── confidence_assigner.py # High / Medium / Low confidence classifier
│   │   ├── error_categorizer.py   # Structured error → user-facing message mapper
│   │   ├── pdf_generator.py       # WeasyPrint PDF renderer + Markdown fallback
│   │   ├── email_service.py       # SMTP email dispatch with retry logic
│   │   └── web_search.py          # Serper.dev web search enrichment
│   │
│   ├── integrations/              # Outbound channel connectors
│   │   ├── webhooks.py            # Slack & CRM webhooks (async httpx)
│   │   ├── sheets.py              # Google Sheets logging (asyncio.to_thread)
│   │   └── drive.py               # Google Drive PDF archival (asyncio.to_thread)
│   │
│   ├── utils/                     # Infrastructure primitives
│   │   ├── circuit_breaker.py     # Circuit Breaker (CLOSED / OPEN / HALF_OPEN)
│   │   ├── retry.py               # Exponential backoff + jitter retry decorator
│   │   ├── timeout.py             # Async timeout decorator & context manager
│   │   └── validation.py          # URL validation & Pydantic schema helpers
│   │
│   ├── templates/                 # Industry fallback content templates
│   ├── test_smoke.py              # Offline smoke tests (no external services needed)
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/                   # Next.js App Router (React)
│   └── public/                    # Static assets
│
├── scripts/
│   ├── setup.sh                   # One-time environment setup
│   └── start_all.sh               # Start FastAPI + Celery + Next.js
│
└── output/                        # Generated PDF / Markdown reports (git-ignored)
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System diagnostics & configuration status |
| `POST` | `/api/leads` | Submit a new lead for async processing |
| `GET` | `/api/leads/{id}/status` | Poll pipeline progress |
| `GET` | `/api/leads/{id}/pdf` | Download the generated intelligence report |

### Example: Submit a Lead

```bash
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "email": "jane@example.com",
    "company": "Vercel",
    "website": "https://vercel.com",
    "industry": "Cloud Infrastructure"
  }'
```

**Response (`202 Accepted`):**
```json
{
  "lead_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "submitted",
  "message": "Lead submitted and enqueued for enrichment pipeline."
}
```

### Example: Poll for Completion

```bash
curl http://localhost:8000/api/leads/a1b2c3d4/status
```

**Response — In Progress (`200 OK`):**
```json
{
  "lead_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "processing",
  "current_step": "scraping_company_website",
  "progress": 0.25,
  "is_complete": false,
  "error": null
}
```

**Response — Completed (`200 OK`):**
```json
{
  "lead_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "complete",
  "current_step": "complete",
  "progress": 1.0,
  "is_complete": true,
  "error": null,
  "quality_score": 0.92,
  "confidence_level": "High"
}
```

### Example: Download Report

```bash
curl -O http://localhost:8000/api/leads/a1b2c3d4/pdf
```

---

## 🛠️ Development

### Running Tests

The smoke test suite runs fully offline — no Redis, OpenRouter, or SMTP required.

```bash
cd backend
source venv/bin/activate
python -m pytest test_smoke.py -v
```

The suite covers:
- Module import validation
- Pydantic model instantiation & field validators
- URL validation & normalisation utilities
- AI hallucination / repetition detection
- Quality scoring & confidence assignment
- Error categorisation & user-facing messages
- Retry engine (success, partial failure, non-retryable errors)

### Environment Reference

All configuration is managed through `backend/.env`. See [`backend/.env.example`](backend/.env.example) for a fully annotated reference with every available variable.

### Database

- **Development** (default): SQLite — zero config, runs instantly.
- **Production**: Set `DATABASE_URL=postgresql://user:pass@host:5432/lead_autopilot` in `.env`. The engine automatically switches to a connection-pooled PostgreSQL driver (`psycopg2-binary`) with `NullPool` for Celery worker safety.

---

## 🔍 Troubleshooting

### WeasyPrint macOS Library Errors
If you see errors related to `cairo`, `pango`, or shared libraries when generating PDFs on macOS, run:
```bash
brew install pango cairo libffi gdk-pixbuf
```
If errors persist, you may need to explicitly export the library paths in your shell profile:
```bash
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_FALLBACK_LIBRARY_PATH
```

---

## 🔒 Security Notes

* **No tracking** — The system does not phone home.
* **Ephemeral processing** — API keys and tokens are held only in memory during task execution.
* **SSL verification** — Disabled in the basic HTTP scraper to support SMB websites with self-signed or misconfigured certificates. Only public HTML is read; no credentials are transmitted. This can be re-enabled via `verify=True` in `services/scraper.py` for stricter environments.

---

## 📄 License

MIT © [shravansumanthanan](https://github.com/shravansumanthanan)

<div align="center">
  <i>Engineered for Reliability</i>
</div>
