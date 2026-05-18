import os
import logging
import httpx
from models import EnrichedCompanyData

logger = logging.getLogger(__name__)

async def send_slack_notification(enriched: EnrichedCompanyData, pdf_url: str = None) -> bool:
    """Send a notification to Slack when a high-quality lead is processed."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return False

    lead = enriched.lead
    quality = enriched.data_quality_score
    
    # Optional formatting to highlight high-quality leads
    emoji = "🔥" if quality > 0.7 else "🔔"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} New Lead Processed: {lead.company}"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Name:*\n{lead.name}"},
                {"type": "mrkdwn", "text": f"*Email:*\n{lead.email}"},
                {"type": "mrkdwn", "text": f"*Industry:*\n{lead.industry}"},
                {"type": "mrkdwn", "text": f"*Quality Score:*\n{quality:.2f}/1.00"},
            ]
        }
    ]

    if enriched.analysis.executive_summary:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Executive Summary:*\n{enriched.analysis.executive_summary[:300]}..."
            }
        })

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json={"blocks": blocks})
            response.raise_for_status()
            logger.info(f"Slack notification sent for {lead.company}")
            return True
    except Exception as e:
        logger.error(f"Failed to send Slack notification for {lead.company}: {e}")
        return False


async def send_crm_webhook(enriched: EnrichedCompanyData, pdf_url: str = None) -> bool:
    """Send the raw enriched JSON payload to a CRM or Zapier webhook."""
    webhook_url = os.getenv("CRM_WEBHOOK_URL")
    if not webhook_url:
        return False

    # Dump the enriched data into a JSON dictionary
    payload = enriched.model_dump(mode="json")
    if pdf_url:
        payload["pdf_url"] = pdf_url

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"CRM webhook payload sent for {enriched.lead.company}")
            return True
    except Exception as e:
        logger.error(f"Failed to send CRM webhook for {enriched.lead.company}: {e}")
        return False
