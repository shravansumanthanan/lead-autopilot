import asyncio
import logging
from datetime import datetime, timezone
from celery_app import celery_app

from sqlalchemy.orm.attributes import flag_modified

from core_models import LeadSubmission, EnrichedCompanyData, PipelineStep
from database import SessionLocal, DBLeadStatus
from workflows.report_pipeline import run_enrichment_pipeline
from services.pdf_generator import generate_report_pdf
from services.email_service import send_report_email
from services.error_categorizer import ErrorCategorizerService
from integrations.sheets import log_lead_to_sheets
from integrations.drive import upload_pdf_to_drive
from integrations.webhooks import send_slack_notification, send_crm_webhook

logger = logging.getLogger(__name__)
error_categorizer = ErrorCategorizerService()

def update_db_status(db, lead_id: str, current_step: PipelineStep, completed_step: PipelineStep | None = None, **kwargs):
    status = db.query(DBLeadStatus).filter(DBLeadStatus.lead_id == lead_id).first()
    if status:
        status.current_step = current_step.value
        if completed_step:
            # Reassign to a new list so SQLAlchemy's JSON column change tracker
            # detects the mutation. In-place .append() on a JSON column is
            # not automatically tracked without flag_modified.
            steps = list(status.steps_completed or [])
            steps.append(completed_step.value)
            status.steps_completed = steps
            # Belt-and-suspenders: explicitly mark the JSON column as dirty
            # so SQLAlchemy's unit-of-work always flushes the new value.
            flag_modified(status, "steps_completed")
        for k, v in kwargs.items():
            setattr(status, k, v)
        db.commit()
    return status

async def _async_process_lead_pipeline(lead_id: str, lead_dict: dict):
    lead = LeadSubmission(**lead_dict)
    db = SessionLocal()
    try:
        update_db_status(db, lead_id, PipelineStep.VALIDATING, PipelineStep.SUBMITTED)
        logger.info(f"[{lead_id}] Pipeline started for {lead.company}")

        update_db_status(db, lead_id, PipelineStep.ENRICHING, PipelineStep.VALIDATING)
        logger.info(f"[{lead_id}] Starting enrichment...")

        enriched: EnrichedCompanyData = await run_enrichment_pipeline(lead)
        logger.info(f"[{lead_id}] Enrichment complete (quality: {enriched.data_quality_score:.2f}, confidence: {enriched.confidence_level})")

        update_db_status(db, lead_id, PipelineStep.GENERATING_PDF, PipelineStep.ENRICHING)
        logger.info(f"[{lead_id}] Generating PDF report...")

        pdf_path = generate_report_pdf(enriched)
        update_db_status(db, lead_id, PipelineStep.GENERATING_PDF, pdf_path=pdf_path)
        logger.info(f"[{lead_id}] PDF generated: {pdf_path}")

        update_db_status(db, lead_id, PipelineStep.SENDING_EMAIL, PipelineStep.GENERATING_PDF)
        logger.info(f"[{lead_id}] Sending email to {lead.email}...")

        email_sent = await send_report_email(
            to_email=lead.email,
            prospect_name=lead.name,
            company_name=lead.company,
            industry=lead.industry,
            pdf_path=pdf_path,
        )
        update_db_status(db, lead_id, PipelineStep.SENDING_EMAIL, email_sent=email_sent)

        update_db_status(db, lead_id, PipelineStep.LOGGING, PipelineStep.SENDING_EMAIL)

        report_status = "complete" if email_sent else "pdf_only"

        try:
            await log_lead_to_sheets(
                name=lead.name,
                email=lead.email,
                company=lead.company,
                website=str(lead.website),
                industry=lead.industry,
                report_status=report_status,
                pdf_path=pdf_path,
            )
        except Exception as e:
            logger.warning(f"[{lead_id}] Sheets logging failed: {e}")

        # ── Step 6: Webhooks (CRM/Slack) ───────────────────────────────
        drive_link: str | None = None
        try:
            drive_link = await upload_pdf_to_drive(pdf_path, lead.company)
            if drive_link:
                logger.info(f"[{lead_id}] PDF archived to Drive: {drive_link}")
        except Exception as e:
            logger.warning(f"[{lead_id}] Drive upload failed: {e}")

        try:
            await send_slack_notification(enriched, pdf_url=drive_link)
        except Exception as e:
            logger.warning(f"[{lead_id}] Slack notification failed: {e}")

        try:
            await send_crm_webhook(enriched, pdf_url=drive_link)
        except Exception as e:
            logger.warning(f"[{lead_id}] CRM webhook failed: {e}")

        update_db_status(db, lead_id, PipelineStep.COMPLETE, PipelineStep.LOGGING, completed_at=datetime.now(timezone.utc))
        
        if enriched.confidence_level != "High":
            logger.info(f"[{lead_id}] Pipeline complete for {lead.company} (PARTIAL_SUCCESS: {enriched.confidence_level} Confidence)")
        else:
            logger.info(f"[{lead_id}] Pipeline complete for {lead.company}")

    except Exception as e:
        error_event = error_categorizer.categorize_and_log(
            error=e,
            lead_id=lead_id,
            component="pipeline",
        )
        update_db_status(
            db, lead_id, PipelineStep.ERROR,
            error_message=error_event.user_facing_message,
        )
    finally:
        db.close()

@celery_app.task
def process_lead_task(lead_id: str, lead_dict: dict):
    """Synchronous Celery task that wraps the async pipeline."""
    asyncio.run(_async_process_lead_pipeline(lead_id, lead_dict))
