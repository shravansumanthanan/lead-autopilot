"""
Google Drive Integration.

Archives generated PDF reports to a Google Drive folder.
All blocking Google API I/O is offloaded to a thread pool via
asyncio.to_thread() so the asyncio event loop is never stalled.
Gracefully skips if credentials are not configured.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _sync_upload_to_drive(pdf_path: str, company_name: str) -> str | None:
    """
    Synchronous inner function that performs all blocking Google Drive API I/O.

    This is intentionally synchronous and must only be called via
    asyncio.to_thread() to prevent blocking the event loop.
    """
    creds_file = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE", "")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

    if not creds_file or not os.path.exists(creds_file):
        logger.info("Google Drive credentials not configured — skipping")
        return None

    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found for upload: {pdf_path}")
        return None

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)
        service = build("drive", "v3", credentials=credentials)

        # Prepare file metadata
        file_name = f"{company_name.replace(' ', '_')}_Report.pdf"
        file_metadata: dict = {"name": file_name, "mimeType": "application/pdf"}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(pdf_path, mimetype="application/pdf", resumable=True)

        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        # Make the file viewable by anyone with the link
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        link = file.get("webViewLink", "")
        logger.info(f"PDF uploaded to Google Drive: {link}")
        return link

    except ImportError:
        logger.warning(
            "google-api-python-client not installed — skipping Drive upload"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to upload to Google Drive: {e}")
        return None


async def upload_pdf_to_drive(pdf_path: str, company_name: str) -> str | None:
    """
    Upload a PDF report to Google Drive without blocking the event loop.

    All blocking Google API I/O is delegated to asyncio.to_thread(),
    which runs it on a separate OS thread from the default ThreadPoolExecutor.

    Args:
        pdf_path: Local path to the PDF file.
        company_name: Company name (used for the Drive file name).

    Returns:
        Shareable link if successful, None otherwise.
    """
    return await asyncio.to_thread(_sync_upload_to_drive, pdf_path, company_name)
