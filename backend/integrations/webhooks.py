"""
Webhook integrations for Slack and CRM notifications.

Uses httpx.AsyncClient for fully non-blocking HTTP calls to prevent
event loop stalls when the FastAPI/Celery async pipeline is in flight.
"""

import logging
import os
from typing import Optional

import httpx

from core_models import EnrichedCompanyData

logger = logging.getLogger(__name__)


async def _post_json(url: str, payload: dict) -> bool:
    """
    POST a JSON payload to a URL using httpx.AsyncClient.

    Fully non-blocking — does NOT stall the asyncio event loop.
    Returns True on a 2xx response.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Webhook POST to {url} returned HTTP {e.response.status_code}: {e}"
        )
        return False
    except httpx.RequestError as e:
        logger.error(f"Webhook POST to {url} failed (network error): {e}")
        return False


async def send_slack_notification(
    enriched: EnrichedCompanyData, pdf_url: Optional[str] = None
) -> bool:
    """Send a notification to Slack when a lead is processed."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return False

    lead = enriched.lead
    quality = enriched.data_quality_score

    emoji = "\U0001f525" if quality > 0.7 else "\U0001f514"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} New Lead Processed: {lead.company}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Name:*\n{lead.name}"},
                {"type": "mrkdwn", "text": f"*Email:*\n{lead.email}"},
                {"type": "mrkdwn", "text": f"*Industry:*\n{lead.industry}"},
                {"type": "mrkdwn", "text": f"*Quality Score:*\n{quality:.2f}/1.00"},
                {"type": "mrkdwn", "text": f"*Confidence:*\n{enriched.confidence_level}"},
            ],
        },
    ]

    if enriched.analysis.executive_summary:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Executive Summary:*\n{enriched.analysis.executive_summary[:300]}...",
                },
            }
        )

    if pdf_url:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{pdf_url}|📄 View PDF Report>",
                },
            }
        )

    try:
        success = await _post_json(webhook_url, {"blocks": blocks})
        if success:
            logger.info(f"Slack notification sent for {lead.company}")
        return success
    except Exception as e:
        logger.error(f"Failed to send Slack notification for {lead.company}: {e}")
        return False


async def send_crm_webhook(
    enriched: EnrichedCompanyData, pdf_url: Optional[str] = None
) -> bool:
    """Send the raw enriched JSON payload to a CRM or Zapier webhook."""
    webhook_url = os.getenv("CRM_WEBHOOK_URL")
    if not webhook_url:
        return False

    payload = enriched.model_dump(mode="json")
    if pdf_url:
        payload["pdf_url"] = pdf_url

    try:
        success = await _post_json(webhook_url, payload)
        if success:
            logger.info(f"CRM webhook payload sent for {enriched.lead.company}")
        return success
    except Exception as e:
        logger.error(f"Failed to send CRM webhook for {enriched.lead.company}: {e}")
        return False
