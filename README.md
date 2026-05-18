# Lead Autopilot

> Automated lead intake → company enrichment → PDF report generation → email delivery.

When a prospect submits a form, the system automatically:

1. **Captures & validates** lead information (Pydantic)
2. **Enriches** company data — Firecrawl (optional, JS-aware) → HTTPX+BS4 scraper → Serper.dev web search (optional)
3. **Generates** a personalized 6-page PDF audit report (WeasyPrint + Jinja2)
4. **Sends** the report to the prospect via email (Gmail SMTP)
5. *(Bonus)* Logs to Google Sheets + archives PDF to Google Drive

---

## Architecture

```
┌────────────────────┐      POST /api/leads
│  Vite Frontend     │ ──────────────────────► ┌──────────────────────────────────┐
│  (Lead Form)       │ ◄──────────────────────  │  FastAPI Backend                 │
│                    │      202 + lead_id        │                                  │
│  GET /status poll  │ ──────────────────────►  │  Background Pipeline:            │
└────────────────────┘                          │  ┌──────────┐  ┌──────────────┐ │
                                                │  │Firecrawl │→ │  BS4 Scraper │ │
                                                │  └──────────┘  └──────────────┘ │
                                                │        ↓                         │
                                                │  ┌──────────┐                   │
                                                │  │ Serper.dev│ (web search)      │
                                                │  └──────────┘                   │
                                                │        ↓                         │
                                                │  ┌──────────┐                   │
                                                │  │Qwen (via │ (AI analysis)      │
                                                │  │OpenRouter│                   │
                                                │  └──────────┘                   │
                                                │        ↓                         │
                                                │  ┌──────────┐  ┌──────────────┐ │
                                                │  │WeasyPrint│  │ Gmail SMTP   │ │
                                                │  │  PDF Gen │  │ Email Send   │ │
                                                │  └──────────┘  └──────────────┘ │
                                                └──────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|:--|:--|
| Frontend | Vite + Vanilla JS/CSS (dark glassmorphism design) |
| Backend | Python 3.13 + FastAPI |
| Scraping (primary) | Firecrawl API (JS-aware, optional) |
| Scraping (fallback) | HTTPX + BeautifulSoup4 |
| Web Search | Serper.dev Google Search API (optional) |
| AI Analysis | Qwen via OpenRouter (OpenAI-compatible SDK) |
| PDF Generation | WeasyPrint + Jinja2 |
| Email | Gmail SMTP (smtplib) |
| Sheets (bonus) | gspread |
| Drive (bonus) | google-api-python-client |

---

## Quick Start

### Option A — One Command

```bash
./setup.sh
```

Then edit `backend/.env` and start both servers as prompted.

### Option B — Manual

**Prerequisites (macOS):**
```bash
# WeasyPrint system libraries
brew install pango cairo libffi gdk-pixbuf

# Python 3.11+ and Node 18+
brew install python@3.13 node
```

**Backend:**
```bash
cd backend
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# ← Edit .env with your API keys
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Environment Variables

### Required

| Variable | Description | Where to get |
|:--|:--|:--|
| `OPENROUTER_API_KEY` | OpenRouter API key | [openrouter.ai](https://openrouter.ai) |
| `SMTP_EMAIL` | Gmail address | Your Gmail |
| `SMTP_PASSWORD` | Gmail App Password | [Google Account → Security → App Passwords](https://myaccount.google.com/apppasswords) |

### Optional Enrichment (increases report quality)

| Variable | Description | Where to get |
|:--|:--|:--|
| `OPENROUTER_MODEL` | Model name (default: `qwen/qwen3-235b-a22b`) | Any OpenRouter model |
| `FIRECRAWL_API_KEY` | Better JS-aware scraping | [firecrawl.dev](https://firecrawl.dev) |
| `SERPER_API_KEY` | Google search context | [serper.dev](https://serper.dev) |

### Branding (customise the report)

| Variable | Default | Description |
|:--|:--|:--|
| `BUSINESS_NAME` | `Lead Autopilot` | Your company name (shown on PDF) |
| `BUSINESS_TAGLINE` | `Data-Driven Insights` | PDF cover tagline |
| `BUSINESS_EMAIL` | `contact@example.com` | Contact email on PDF |
| `BUSINESS_PHONE` | *(empty)* | Phone on PDF |
| `BUSINESS_WEBSITE` | *(empty)* | Website on PDF |

### Bonus Integrations

| Variable | Description |
|:--|:--|
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Path to service account JSON |
| `GOOGLE_SHEET_NAME` | Spreadsheet name (created if not exists) |
| `GOOGLE_DRIVE_CREDENTIALS_FILE` | Path to service account JSON |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive folder ID for PDF archival |

---

## API Reference

| Method | Endpoint | Description |
|:--|:--|:--|
| `POST` | `/api/leads` | Submit a lead → starts pipeline |
| `GET` | `/api/leads/{id}/status` | Poll pipeline status |
| `GET` | `/api/leads/{id}/pdf` | Download generated PDF |
| `GET` | `/api/health` | Check which integrations are configured |

Interactive docs: **http://localhost:8000/docs**

---

## Error Handling Strategy

Every layer has fallbacks — a report is **always** generated:

| Failure | Fallback |
|:--|:--|
| Firecrawl fails/not configured | Falls through to HTTPX+BS4 scraper |
| Scraper blocked/fails | AI proceeds with company name + industry only |
| Serper not configured | Skipped silently |
| AI analysis fails | Fallback text generated, report still created |
| Email send fails | PDF still generated and downloadable via API |
| Sheets/Drive fails | Logged as warning, pipeline continues |

---

## Project Structure

```
lead-autopilot/
├── setup.sh                     # One-command setup
├── frontend/
│   ├── index.html               # Lead intake form
│   ├── style.css                # Dark glassmorphism design system
│   ├── main.js                  # Form logic, validation, status polling
│   └── vite.config.js           # Dev proxy to backend
├── backend/
│   ├── main.py                  # FastAPI app, routes, pipeline orchestration
│   ├── models.py                # Pydantic models (LeadSubmission, AIAnalysis, etc.)
│   ├── enrichment/
│   │   ├── pipeline.py          # Orchestrates all enrichment steps
│   │   ├── scraper.py           # HTTPX + BeautifulSoup4 scraper
│   │   ├── firecrawl_scraper.py # Firecrawl integration (optional)
│   │   ├── web_search.py        # Serper.dev Google search (optional)
│   │   └── ai_analyzer.py      # Qwen via OpenRouter
│   ├── pdf/
│   │   ├── generator.py         # WeasyPrint PDF generation
│   │   └── templates/
│   │       └── report.html      # Jinja2 report template (6 pages)
│   ├── email_service/
│   │   └── sender.py            # SMTP email with HTML body + PDF attachment
│   ├── integrations/
│   │   ├── sheets.py            # Google Sheets logging (bonus)
│   │   └── drive.py             # Google Drive archival (bonus)
│   ├── requirements.txt
│   └── .env.example
├── output/                      # Generated PDFs (gitignored)
└── README.md
```

---

## Design Decisions

1. **OpenRouter + Qwen**: Uses OpenAI-compatible SDK — swap any model by changing `OPENROUTER_MODEL`. The Qwen3-235B model produces analyst-quality structured output.

2. **Firecrawl → BS4 fallback**: Modern JS-heavy sites (React/Next.js) don't render well with raw HTTPX. Firecrawl handles them cleanly. BS4 covers the rest.

3. **Serper.dev**: Website scraping only sees what the company says about themselves. Search results add third-party context, news, and knowledge graph facts — making the AI analysis significantly more grounded.

4. **FastAPI BackgroundTasks**: No Celery/Redis overhead for a prototype. The frontend polls `/status` every 2 seconds. For production scale, swap to Celery with Redis.

5. **WeasyPrint table-based layout**: WeasyPrint has incomplete CSS grid/flex support. The template uses `<table>` for multi-column layouts — reliable across all WeasyPrint versions.

6. **In-memory status store**: A `dict` in the FastAPI process. Simple, zero dependencies. For production: add Redis or a DB.

---

## Setting Up Gmail App Password

1. Enable 2-Step Verification at [myaccount.google.com/security](https://myaccount.google.com/security)
2. Go to **Security → App Passwords**
3. Create a new app password (name it "Lead Autopilot")
4. Use the 16-character code as `SMTP_PASSWORD` in `.env`

## Setting Up Google Sheets/Drive (Bonus)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON credentials file
4. Save the JSON file as `backend/service_account.json`
5. Share your target Google Sheet with the service account email
6. Set in `.env`:
   ```
   GOOGLE_SHEETS_CREDENTIALS_FILE=service_account.json
   GOOGLE_SHEET_NAME=Lead Autopilot Tracker
   GOOGLE_DRIVE_CREDENTIALS_FILE=service_account.json
   GOOGLE_DRIVE_FOLDER_ID=<your-folder-id>
   ```

---

## License

MIT
