import io
import logging
from typing import Tuple

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

logger = logging.getLogger(__name__)

class PDFValidator:
    """Valiates PDF files for integration into the reporting system."""
    
    def __init__(self, max_size_mb: int = 10):
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def validate_pdf(self, file_content: bytes) -> Tuple[bool, str]:
        """
        Validate a PDF file's size, magic bytes, and readable integrity.
        Returns a tuple of (is_valid, error_message).
        """
        if not file_content:
            return False, "File is empty."

        if len(file_content) > self.max_size_bytes:
            return False, f"File exceeds maximum size of {self.max_size_bytes / (1024*1024):.1f} MB."

        # Check PDF header magic bytes
        if not file_content.startswith(b'%PDF-'):
            return False, "File is not a valid PDF (invalid magic bytes)."

        if PyPDF2 is None:
            logger.warning("PyPDF2 is not installed, skipping integrity check.")
            return True, ""

        try:
            # Attempt to natively parse the file to catch corruption
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            num_pages = len(pdf_reader.pages)
            if num_pages == 0:
                return False, "PDF file has no pages."
        except Exception as e:
            logger.error(f"PDF integrity check failed: {e}")
            return False, f"PDF file is corrupt or unreadable: {str(e)}"

        return True, ""
