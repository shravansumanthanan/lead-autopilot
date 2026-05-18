import pytest
from services.pdf_validator import PDFValidator

def test_validate_pdf_empty():
    validator = PDFValidator()
    is_valid, msg = validator.validate_pdf(b"")
    assert not is_valid
    assert "empty" in msg

def test_validate_pdf_too_large():
    validator = PDFValidator(max_size_mb=1)
    large_content = b"a" * (2 * 1024 * 1024)
    is_valid, msg = validator.validate_pdf(large_content)
    assert not is_valid
    assert "exceeds maximum size" in msg

def test_validate_pdf_invalid_magic_bytes():
    validator = PDFValidator()
    content = b"Not a PDF file"
    is_valid, msg = validator.validate_pdf(content)
    assert not is_valid
    assert "invalid magic bytes" in msg

def test_validate_pdf_corrupt():
    validator = PDFValidator()
    # Has magic bytes but is invalid pdf structure
    content = b"%PDF-1.4\nSome garbage here"
    is_valid, msg = validator.validate_pdf(content)
    assert not is_valid
    assert "corrupt or unreadable" in msg
