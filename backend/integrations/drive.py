"""
Google Drive Integration (Bonus).

Archives generated PDF reports to a Google Drive folder.
Gracefully skips if credentials are not configured.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


async def upload_pdf_to_drive(pdf_path: str, company_name: str) -> str | None:
    """
    Upload a PDF report to Google Drive.

    Args:
        pdf_path: Local path to the PDF file.
        company_name: Company name (used for the Drive file name).

    Returns:
        Shareable link if successful, None otherwise.
        Silently skips if credentials are not configured.
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
        file_metadata = {"name": file_name, "mimeType": "application/pdf"}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(pdf_path, mimetype="application/pdf", resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        # Make the file viewable by anyone with the link
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        link = file.get("webViewLink", "")
        logger.info(f"PDF uploaded to Google Drive: {link}")
        return link

    except ImportError:
        logger.warning("google-api-python-client not installed — skipping Drive upload")
        return None
    except Exception as e:
        logger.error(f"Failed to upload to Google Drive: {e}")
        return None
