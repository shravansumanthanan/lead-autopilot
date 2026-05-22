"""
Google Sheets Integration.

Logs each lead's data to a Google Sheet for live tracking.
All blocking Google API I/O is offloaded to a thread pool via
asyncio.to_thread() so the asyncio event loop is never stalled.
Gracefully skips if credentials are not configured.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _sync_log_to_sheets(
    name: str,
    email: str,
    company: str,
    website: str,
    industry: str,
    report_status: str,
    pdf_path: str,
) -> bool:
    """
    Synchronous inner function that performs all blocking Google API I/O.

    This is intentionally synchronous and must only be called via
    asyncio.to_thread() to prevent blocking the event loop.
    """
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Lead Autopilot Tracker")

    if not creds_file or not os.path.exists(creds_file):
        logger.info("Google Sheets credentials not configured — skipping")
        return False

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)
        gc = gspread.authorize(credentials)

        # Open or create the spreadsheet
        try:
            spreadsheet = gc.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            spreadsheet = gc.create(sheet_name)
            worksheet = spreadsheet.sheet1
            worksheet.update(
                "A1:H1",
                [["Name", "Email", "Company", "Website",
                  "Industry", "Timestamp (UTC)", "Report Status", "PDF Path"]],
            )
            logger.info(f"Created new Google Sheet: {sheet_name}")

        worksheet = spreadsheet.sheet1
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        worksheet.append_row(
            [name, email, company, website, industry, timestamp, report_status, pdf_path]
        )

        logger.info(f"Lead logged to Google Sheets: {company} ({email})")
        return True

    except ImportError:
        logger.warning("gspread not installed — skipping Sheets logging")
        return False
    except Exception as e:
        logger.error(f"Failed to log to Google Sheets: {e}")
        return False


async def log_lead_to_sheets(
    name: str,
    email: str,
    company: str,
    website: str,
    industry: str,
    report_status: str,
    pdf_path: str = "",
) -> bool:
    """
    Append lead data to a Google Sheet without blocking the event loop.

    All blocking Google API I/O is delegated to asyncio.to_thread(),
    which runs it on a separate OS thread from the default ThreadPoolExecutor.

    Returns True if logged successfully, False otherwise.
    """
    return await asyncio.to_thread(
        _sync_log_to_sheets,
        name,
        email,
        company,
        website,
        industry,
        report_status,
        pdf_path,
    )
