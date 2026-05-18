"""
Lead Autopilot — FastAPI Backend

Main application that orchestrates the entire lead processing pipeline.
"""

import logging
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import DBLeadStatus, init_db, get_db
from core_models import (
    LeadSubmission,
    LeadSubmitResponse,
    PipelineStep,
    StatusResponse,
)
from tasks import process_lead_task

# ── Configuration ────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lead-autopilot")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    init_db()
    yield

# ── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Lead Autopilot",
    description="Automated lead intake, enrichment, and report delivery system",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# ── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Lead Autopilot",
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "smtp_configured": bool(os.getenv("SMTP_EMAIL") and os.getenv("SMTP_PASSWORD")),
        "sheets_configured": bool(os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")),
        "drive_configured": bool(os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE")),
    }


@app.post("/api/leads", response_model=LeadSubmitResponse, status_code=202)
async def submit_lead(lead: LeadSubmission, db: Session = Depends(get_db)):
    """Submit a new lead for processing."""
    lead_id = str(uuid.uuid4())[:8]

    db_status = DBLeadStatus(
        lead_id=lead_id,
        company_name=lead.company,
        email=lead.email,
        current_step=PipelineStep.SUBMITTED.value,
        steps_completed=[]
    )
    db.add(db_status)
    db.commit()

    # Dispatch to Celery worker
    process_lead_task.delay(lead_id, lead.model_dump(mode="json"))

    logger.info(f"Lead submitted: {lead_id} — {lead.company} ({lead.email})")

    return LeadSubmitResponse(
        lead_id=lead_id,
        message=f"Lead for {lead.company} submitted successfully. Processing has begun.",
        status=PipelineStep.SUBMITTED,
    )


@app.get("/api/leads/{lead_id}/status", response_model=StatusResponse)
async def get_lead_status(lead_id: str, db: Session = Depends(get_db)):
    """Poll for the processing status of a submitted lead."""
    status = db.query(DBLeadStatus).filter(DBLeadStatus.lead_id == lead_id).first()
    if not status:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    return StatusResponse(
        lead_id=status.lead_id,
        current_step=PipelineStep(status.current_step),
        steps_completed=[PipelineStep(s) for s in status.steps_completed],
        error_message=status.error_message,
        is_complete=status.current_step in (PipelineStep.COMPLETE.value, PipelineStep.ERROR.value),
    )


@app.get("/api/leads/{lead_id}/pdf")
async def download_pdf(lead_id: str, db: Session = Depends(get_db)):
    """Download the generated PDF report for a lead."""
    status = db.query(DBLeadStatus).filter(DBLeadStatus.lead_id == lead_id).first()
    if not status:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    if not status.pdf_path or not Path(status.pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    return FileResponse(
        status.pdf_path,
        media_type="application/pdf",
        filename=Path(status.pdf_path).name,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
