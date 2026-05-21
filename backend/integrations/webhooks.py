"""
Webhook integrations for Slack and CRM notifications.

Uses only stdlib (urllib + json) to avoid third-party import issues
in environments where httpx may not be available.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional

from core_models import EnrichedCompanyData

logger = logging.getLogger(__name__)


def _post_json(url: str, payload: dict) -> bool:
    """POST a JSON payload to a URL using stdlib urllib. Returns True on success."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logger.error(f"Webhook POST to {url} failed: {e}")
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

    try:
        success = _post_json(webhook_url, {"blocks": blocks})
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
        success = _post_json(webhook_url, payload)
        if success:
            logger.info(f"CRM webhook payload sent for {enriched.lead.company}")
        return success
    except Exception as e:
        logger.error(f"Failed to send CRM webhook for {enriched.lead.company}: {e}")
        return False
