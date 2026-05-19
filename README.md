# Lead Autopilot

> Automated lead intake → company enrichment → PDF report generation → email delivery.

When a prospect submits a form, the system automatically:

1. **Captures & validates** lead information (Pydantic validation).
2. **Enriches** company data — via Firecrawl (optional, JS-aware), HTTPX+BS4 scraper (fallback), and Serper.dev web search.
3. **Generates** a personalized PDF audit report (WeasyPrint + Jinja2 HTML templating).
4. **Sends** the report to the prospect via email (Gmail SMTP or Ethereal mock).
5. *(Bonus)* **Logs** to Google Sheets + archives the PDF to Google Drive.

---

## 🏗️ Architecture & Engineering Decisions

```text
┌────────────────────┐      POST /api/leads
│  Next.js Frontend  │ ──────────────────────► ┌──────────────────────────────────┐
│  (React/Tailwind)  │ ◄──────────────────────  │  FastAPI Backend                 │
│                    │      202 + lead_id        │                                  │
│  GET /status poll  │ ──────────────────────►  │  Background Pipeline (Celery):   │
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

### Thoughtful System Design: Real-World Resilience
A core constraint of lead generation is that **a prospect must always receive an interaction, regardless of system failures.** This architecture leverages resilient fallbacks at every stage:

1. **Scraping Limitations (Firecrawl → BS4):** Modern React/Next.js SPA sites do not render content for raw HTTP requests. We attempt to use Firecrawl to execute JS and fetch semantic DOM content. If the API is missing or fails, we gracefully fallback to a standard HTTPX + BeautifulSoup4 scraper.
2. **Missing Data & Circuit Breakers (AI Analysis):** If scraping fails completely (e.g., Cloudflare blocking), the pipeline doesn't crash. It passes just the company name and industry to the AI model. If the OpenRouter AI connection times out or fails schema validation, the system falls back to a deterministic `FallbackContentGenerator` that produces a generic, industry-standard report.
3. **Task Queue Architecture (Celery + Redis):** Unlike simple prototypes that use `BackgroundTasks`, this pipeline uses a true async worker queue (Celery + Redis). This ensures the FastAPI server thread isn't blocked by slow operations like WeasyPrint rendering or 45-second AI timeouts, enabling scalability.
4. **Validation and Schema Strictness:** We use Pydantic models extensively to enforce schema validation on both user inputs and AI-generated outputs, preventing hallucinated keys from breaking the PDF generation.
5. **Bonus Capabilities (Drive & Sheets):** Uses Google APIs to seamlessly track leads and archive PDFs asynchronously. These steps use a fire-and-forget pattern so that a failure in internal logging does not prevent the user from receiving their email.

---

## 🛠️ Quick Start & Setup

### Prerequisites
- Docker (for running Redis locally)
- Node.js v18+
- Python 3.12+
- `brew install pango cairo libffi gdk-pixbuf` (macOS requirements for WeasyPrint PDF Generation)

### 1. Environment Configuration

Copy the example environment file:
```bash
cd backend
cp .env.example .env
```

**Security Note:** All API keys are excluded from the repository. You must add your own keys for the pipeline to utilize its full capabilities.

| Variable | Description | Recommended Testing Keys |
|:--|:--|:--|
| `OPENROUTER_API_KEY` | (Required for AI) Analyzes scraped context. | Get a free key at [openrouter.ai](https://openrouter.ai) |
| `SMTP_EMAIL` / `SMTP_PASSWORD` | (Required) Sends the final PDF. | Your Gmail + [App Password](https://myaccount.google.com/apppasswords) |
| `FIRECRAWL_API_KEY` | (Optional) Enables JS rendering scraper. | Get a key at [firecrawl.dev](https://firecrawl.dev) |
| `SERPER_API_KEY` | (Optional) Adds Google Search context. | Get a key at [serper.dev](https://serper.dev) |

*If keys are omitted, the application will still run using deterministic fallbacks and mock loggers.*

### 2. Start the Stack

We have provided a unified script to start the Frontend, Backend, Celery Worker, and Redis Database simultaneously:

```bash
./start_all.sh
```

The system will be available at:
- Frontend UI: [http://localhost:5173](http://localhost:5173) (Proxies API requests cleanly via `next.config.ts`)
- Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

*(Logs for each service will be written to `frontend_prod.log`, `backend.log`, and `celery.log` in the root directory).*

---

## 🧪 Testing

The backend includes a comprehensive test suite covering the entire pipeline execution and pydantic schema validation. We use `CELERY_TASK_ALWAYS_EAGER=True` to run the Celery pipeline synchronously during tests without requiring Redis.

```bash
cd backend
source venv/bin/activate
pytest
```

---

## 💡 Assumptions, Limitations & Tradeoffs

1. **Synchronous PDF Generation:** WeasyPrint can be resource-intensive. While pushed to a Celery worker, it still synchronously blocks the worker thread. At high scale, PDF generation should be moved to a dedicated microservice.
2. **Database:** The current implementation uses SQLite for simplicity and portability in an interview context. For production, PostgreSQL should be used for concurrent `DBLeadStatus` updates.
3. **UI Polling vs WebSockets:** The Next.js frontend uses simple long-polling (`setInterval` every 2s) to check the pipeline status. While WebSockets would be more efficient, polling is significantly easier to deploy and scale in stateless serverless environments (like Vercel) and is an acceptable tradeoff for a 15-second pipeline workflow.
4. **Error Messaging:** Rather than exposing raw stack traces to the user when a step fails, the system uses an `ErrorEvent` categorizer to map internal technical faults (e.g., `api_rate_limit`) to user-friendly status updates.

