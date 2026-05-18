import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from services.input_validator import InputValidationService, InputValidationResult

@pytest.fixture
def input_service():
    return InputValidationService()

def test_email_validation_success(input_service):
    data = {"email": "Test.User@Example.com"}
    result = input_service.validate_and_normalize(data)
    
    assert result.is_valid is True
    # email-validator lowercases the domain and standardizes
    assert result.normalized_data["email"] == "Test.User@example.com"
    assert len(result.warnings) == 0

def test_email_validation_failure(input_service):
    data = {"email": "invalid-email"}
    result = input_service.validate_and_normalize(data)
    
    assert result.is_valid is True
    assert result.normalized_data["email"] == "invalid-email"
    assert len(result.warnings) == 1
    assert "Invalid email format" in result.warnings[0]

def test_email_missing(input_service):
    data = {"name": "John"}
    result = input_service.validate_and_normalize(data)
    
    assert result.is_valid is True
    assert len(result.warnings) == 1
    assert "Email is missing or empty" in result.warnings[0]

def test_url_normalization(input_service):
    # Missing scheme
    assert input_service.validate_and_normalize({"website": "example.com"}).normalized_data["website"] == "https://example.com"
    # HTTP instead of HTTPS is kept as is, but scheme is present
    assert input_service.validate_and_normalize({"website": "http://example.com"}).normalized_data["website"] == "http://example.com"
    # Typos in www
    assert input_service.validate_and_normalize({"website": "ww.example.com"}).normalized_data["website"] == "https://www.example.com"
    assert input_service.validate_and_normalize({"website": "https://www,example.com"}).normalized_data["website"] == "https://www.example.com"

def test_text_sanitization(input_service):
    data = {
        "name": "   John   Doe  \n ",
        "company": "<b>ACME</b> Corp",
        "message": "Hello <script>alert(1)</script> World",
        "email": "test@example.com"
    }
    result = input_service.validate_and_normalize(data)
    
    assert result.normalized_data["name"] == "John Doe"
    assert result.normalized_data["company"] == "ACME Corp"
    assert result.normalized_data["message"] == "Hello alert(1) World"

def test_duplicate_submission():
    mock_db = MagicMock()
    # Mocking first() to return a record
    mock_db.execute.return_value.first.return_value = ("existing_record",)
    
    service = InputValidationService(db_session=mock_db)
    
    data = {"email": "test@example.com", "company": "ACME"}
    result = service.validate_and_normalize(data)
    
    assert len(result.warnings) == 1
    assert result.warnings[0] == "Potential duplicate submission detected"
    
def test_no_duplicate_submission():
    mock_db = MagicMock()
    # Mocking first() to return None
    mock_db.execute.return_value.first.return_value = None
    
    service = InputValidationService(db_session=mock_db)
    
    data = {"email": "test@example.com", "company": "ACME"}
    result = service.validate_and_normalize(data)
    
    assert len(result.warnings) == 0
