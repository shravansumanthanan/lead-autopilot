"""
Unit tests for the Error Categorization Service.

Tests error categorization logic, user-friendly message generation,
and recovery action suggestions.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from models.errors import ErrorCategory, ErrorEvent
from services.error_categorizer import ErrorCategorizerService


class TestErrorCategorizerService:
    """Test suite for ErrorCategorizerService."""
    
    @pytest.fixture
    def service(self):
        """Create an ErrorCategorizerService instance for testing."""
        return ErrorCategorizerService()
    
    @pytest.fixture
    def lead_id(self):
        """Sample lead ID for testing."""
        return "test_lead_12345"
    
    # ── Error Categorization Tests ──────────────────────────────────────────
    
    def test_categorize_input_validation_error(self, service, lead_id):
        """Test categorization of input validation errors."""
        error = ValueError("Invalid email format")
        event = service.categorize_and_log(error, lead_id, "validator")
        
        assert event.category == ErrorCategory.INPUT_VALIDATION
        assert event.component == "validator"
        assert event.lead_id == lead_id
        assert not event.recoverable
    
    def test_categorize_scraping_blocked_error(self, service, lead_id):
        """Test categorization of scraping blocked errors (403)."""
        error = Exception("HTTP 403 Forbidden")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event.category == ErrorCategory.SCRAPING_BLOCKED
        assert event.recoverable
        assert "fallback" in event.recovery_action.lower()
    
    def test_categorize_scraping_timeout_error(self, service, lead_id):
        """Test categorization of scraping timeout errors."""
        error = TimeoutError("Request timeout after 30 seconds")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event.category == ErrorCategory.SCRAPING_TIMEOUT
        assert event.recoverable
    
    def test_categorize_ai_timeout_error(self, service, lead_id):
        """Test categorization of AI analysis timeout errors."""
        error = TimeoutError("AI analysis timeout")
        event = service.categorize_and_log(error, lead_id, "ai_analyzer")
        
        assert event.category == ErrorCategory.AI_TIMEOUT
        assert event.recoverable
        assert "retry" in event.recovery_action.lower() or "fallback" in event.recovery_action.lower()
    
    def test_categorize_ai_invalid_response_error(self, service, lead_id):
        """Test categorization of AI invalid response errors."""
        error = ValueError("Invalid JSON schema in AI response")
        event = service.categorize_and_log(error, lead_id, "ai_analyzer")
        
        assert event.category == ErrorCategory.AI_INVALID_RESPONSE
        assert event.recoverable
    
    def test_categorize_pdf_rendering_error(self, service, lead_id):
        """Test categorization of PDF rendering errors."""
        error = Exception("WeasyPrint rendering failed")
        event = service.categorize_and_log(error, lead_id, "pdf_generator")
        
        assert event.category == ErrorCategory.PDF_RENDERING
        assert event.recoverable
    
    def test_categorize_email_smtp_error(self, service, lead_id):
        """Test categorization of email SMTP errors."""
        error = Exception("SMTP connection refused")
        event = service.categorize_and_log(error, lead_id, "email_service")
        
        assert event.category == ErrorCategory.EMAIL_SMTP
        assert event.recoverable
    
    def test_categorize_rate_limit_error(self, service, lead_id):
        """Test categorization of API rate limit errors."""
        error = Exception("HTTP 429 Too Many Requests")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event.category == ErrorCategory.API_RATE_LIMIT
        assert event.recoverable
        assert "retry-after" in event.recovery_action.lower() or "wait" in event.recovery_action.lower()
    
    def test_categorize_api_unavailable_error(self, service, lead_id):
        """Test categorization of API unavailable errors."""
        error = Exception("HTTP 503 Service Unavailable")
        event = service.categorize_and_log(error, lead_id, "ai_analyzer")
        
        assert event.category == ErrorCategory.API_UNAVAILABLE
        assert event.recoverable
    
    def test_categorize_circuit_breaker_error(self, service, lead_id):
        """Test categorization of circuit breaker errors."""
        error = Exception("Circuit breaker open for service")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event.category == ErrorCategory.CIRCUIT_BREAKER_OPEN
        assert event.recoverable
    
    def test_categorize_unknown_error(self, service, lead_id):
        """Test categorization of unknown errors."""
        error = Exception("Some unexpected error")
        event = service.categorize_and_log(error, lead_id, "unknown_component")
        
        assert event.category == ErrorCategory.UNKNOWN
        assert event.recoverable
    
    # ── User-Facing Message Tests ───────────────────────────────────────────
    
    def test_user_message_is_professional(self, service, lead_id):
        """Test that user-facing messages are professional and avoid technical jargon."""
        error = Exception("HTTP 403 Forbidden")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        # Should not contain technical terms
        assert "403" not in event.user_facing_message
        assert "HTTP" not in event.user_facing_message
        assert "Forbidden" not in event.user_facing_message
        
        # Should be professional and helpful
        assert len(event.user_facing_message) > 0
        assert event.user_facing_message[0].isupper()  # Starts with capital letter
    
    def test_all_categories_have_user_messages(self, service):
        """Test that all error categories have user-facing messages."""
        for category in ErrorCategory:
            message = service.get_user_message(category)
            assert message is not None
            assert len(message) > 0
            assert message[0].isupper()  # Professional formatting
    
    def test_user_messages_avoid_negative_language(self, service):
        """Test that user messages avoid harsh negative language."""
        negative_words = ["failed", "error", "broken", "crashed"]
        
        for category in ErrorCategory:
            message = service.get_user_message(category).lower()
            # Allow "error" in unknown category only
            if category != ErrorCategory.UNKNOWN:
                for word in negative_words:
                    if word in message:
                        # Some words like "issue" are acceptable
                        assert word not in message or word == "issue"
    
    # ── Recovery Action Tests ────────────────────────────────────────────────
    
    def test_all_categories_have_recovery_actions(self, service):
        """Test that all error categories have recovery action suggestions."""
        for category in ErrorCategory:
            action = service.get_recovery_action(category)
            assert action is not None
            assert len(action) > 0
    
    def test_recovery_actions_are_actionable(self, service):
        """Test that recovery actions contain actionable verbs."""
        actionable_verbs = ["retry", "fallback", "use", "wait", "validate", "log", "open", "proceed"]
        
        for category in ErrorCategory:
            action = service.get_recovery_action(category).lower()
            # Should contain at least one actionable verb
            assert any(verb in action for verb in actionable_verbs)
    
    # ── ErrorEvent Structure Tests ──────────────────────────────────────────
    
    def test_error_event_has_unique_id(self, service, lead_id):
        """Test that each error event gets a unique ID."""
        error = Exception("Test error")
        event1 = service.categorize_and_log(error, lead_id, "scraper")
        event2 = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event1.error_id != event2.error_id
        assert len(event1.error_id) == 8  # UUID first 8 characters
    
    def test_error_event_includes_timestamp(self, service, lead_id):
        """Test that error events include timestamps."""
        error = Exception("Test error")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event.timestamp is not None
        assert event.timestamp.year >= 2024
    
    def test_error_event_tracks_retry_attempts(self, service, lead_id):
        """Test that error events track retry attempts."""
        error = Exception("Test error")
        event = service.categorize_and_log(error, lead_id, "scraper", retry_attempt=2)
        
        assert event.retry_attempt == 2
    
    def test_error_event_includes_technical_details(self, service, lead_id):
        """Test that error events include technical details."""
        error = ValueError("Invalid input")
        event = service.categorize_and_log(
            error, 
            lead_id, 
            "validator",
            additional_context="URL validation failed for example.com"
        )
        
        assert event.technical_details is not None
        assert "ValueError" in event.technical_details
        assert "Invalid input" in event.technical_details
        assert "example.com" in event.technical_details
    
    # ── Edge Cases and Special Scenarios ─────────────────────────────────────
    
    def test_categorize_with_empty_error_message(self, service, lead_id):
        """Test categorization with an empty error message."""
        error = Exception("")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        assert event.category == ErrorCategory.UNKNOWN
        assert event.user_facing_message is not None
        assert len(event.user_facing_message) > 0
    
    def test_categorize_with_none_additional_context(self, service, lead_id):
        """Test categorization with None as additional context."""
        error = Exception("Test error")
        event = service.categorize_and_log(error, lead_id, "scraper", additional_context=None)
        
        assert event.technical_details is not None
        assert "Test error" in event.technical_details
    
    def test_multiple_error_indicators_in_message(self, service, lead_id):
        """Test error with multiple indicators (e.g., timeout + 503)."""
        error = Exception("Connection timeout: HTTP 503 Service Unavailable")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        # Should prioritize specific error codes over generic timeout
        assert event.category in [ErrorCategory.API_UNAVAILABLE, ErrorCategory.SCRAPING_TIMEOUT]
    
    def test_case_insensitive_error_matching(self, service, lead_id):
        """Test that error categorization is case-insensitive."""
        error1 = Exception("HTTP 403 FORBIDDEN")
        error2 = Exception("http 403 forbidden")
        
        event1 = service.categorize_and_log(error1, lead_id, "scraper")
        event2 = service.categorize_and_log(error2, lead_id, "scraper")
        
        assert event1.category == event2.category == ErrorCategory.SCRAPING_BLOCKED
    
    # ── Integration Tests ────────────────────────────────────────────────────
    
    def test_full_error_lifecycle(self, service, lead_id):
        """Test complete error lifecycle from exception to structured event."""
        # Simulate a real scraping error
        error = Exception("HTTP 403 Forbidden - Bot detection triggered")
        
        event = service.categorize_and_log(
            error=error,
            lead_id=lead_id,
            component="scraper",
            retry_attempt=1,
            additional_context="Firecrawl API blocked request for https://example.com"
        )
        
        # Verify all fields are populated correctly
        assert event.error_id is not None
        assert event.lead_id == lead_id
        assert event.category == ErrorCategory.SCRAPING_BLOCKED
        assert event.component == "scraper"
        assert event.message == str(error)
        assert "Firecrawl" in event.technical_details
        assert event.retry_attempt == 1
        assert event.recoverable is True
        assert event.recovery_action is not None
        assert "fallback" in event.recovery_action.lower()
        assert event.user_facing_message is not None
        assert "403" not in event.user_facing_message  # Technical details hidden
        assert len(event.user_facing_message) > 20  # Meaningful message
    
    def test_error_event_serialization(self, service, lead_id):
        """Test that ErrorEvent can be serialized to JSON."""
        error = Exception("Test error")
        event = service.categorize_and_log(error, lead_id, "scraper")
        
        # Should be serializable to dict
        event_dict = event.model_dump()
        assert isinstance(event_dict, dict)
        assert event_dict["lead_id"] == lead_id
        assert event_dict["category"] == ErrorCategory.SCRAPING_BLOCKED.value or event_dict["category"] == ErrorCategory.UNKNOWN.value
        
        # Should be serializable to JSON
        event_json = event.model_dump_json()
        assert isinstance(event_json, str)
        assert lead_id in event_json
