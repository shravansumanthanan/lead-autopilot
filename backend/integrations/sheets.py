"""
Google Sheets Integration (Bonus).

Logs each lead's data to a Google Sheet for live tracking.
Gracefully skips if credentials are not configured.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


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
    Append lead data to a Google Sheet.

    Returns True if logged successfully, False otherwise.
    Silently skips if credentials are not configured.
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
            # Add headers
            worksheet = spreadsheet.sheet1
            worksheet.update("A1:H1", [[
                "Name", "Email", "Company", "Website",
                "Industry", "Timestamp", "Report Status", "PDF Path"
            ]])
            logger.info(f"Created new Google Sheet: {sheet_name}")

        worksheet = spreadsheet.sheet1
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        worksheet.append_row([
            name, email, company, website,
            industry, timestamp, report_status, pdf_path
        ])

        logger.info(f"Lead logged to Google Sheets: {company} ({email})")
        return True

    except ImportError:
        logger.warning("gspread not installed — skipping Sheets logging")
        return False
    except Exception as e:
        logger.error(f"Failed to log to Google Sheets: {e}")
        return False
