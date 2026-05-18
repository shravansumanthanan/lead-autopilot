# Error Categorization System

This directory contains the error categorization models for the Lead Autopilot production resilience system.

## Overview

The error categorization system provides:
- **Structured error tracking** with standardized categories
- **User-friendly error messages** that hide technical details
- **Recovery action suggestions** for each error type
- **Comprehensive logging** with error IDs and timestamps

## Components

### `errors.py`

Defines the core error models:

- **`ErrorCategory`**: Enum of standardized error categories
  - `INPUT_VALIDATION`: Invalid or malformed input data
  - `SCRAPING_BLOCKED`: Website blocks scraping (403, bot detection)
  - `SCRAPING_TIMEOUT`: Website request timeout
  - `AI_TIMEOUT`: AI analysis timeout
  - `AI_INVALID_RESPONSE`: Invalid JSON or schema validation failure
  - `PDF_RENDERING`: PDF generation failure
  - `EMAIL_SMTP`: Email delivery failure
  - `API_RATE_LIMIT`: API rate limit exceeded (429)
  - `API_UNAVAILABLE`: External service unavailable (503)
  - `CIRCUIT_BREAKER_OPEN`: Circuit breaker preventing calls
  - `UNKNOWN`: Uncategorized errors

- **`ErrorEvent`**: Structured error event model
  - `error_id`: Unique 8-character identifier
  - `lead_id`: Associated lead ID
  - `category`: Error category
  - `component`: Component where error occurred
  - `message`: Technical error message (internal)
  - `technical_details`: Full exception details
  - `timestamp`: UTC timestamp
  - `retry_attempt`: Current retry attempt number
  - `recoverable`: Whether error can be recovered from
  - `recovery_action`: Suggested recovery action
  - `user_facing_message`: Professional message for end users

## Usage

```python
from models.errors import ErrorCategory, ErrorEvent

# Create an error event
error_event = ErrorEvent(
    lead_id="lead_12345",
    category=ErrorCategory.SCRAPING_BLOCKED,
    component="scraper",
    message="HTTP 403 Forbidden",
    technical_details="Firecrawl API returned 403 for https://example.com",
    retry_attempt=1,
    recoverable=True,
    recovery_action="Fallback to basic scraper",
    user_facing_message="We encountered difficulty accessing the website."
)

# Serialize to JSON
error_json = error_event.model_dump_json()
```

## Design Principles

1. **Professional Messaging**: User-facing messages avoid technical jargon and negative language
2. **Actionable Recovery**: Each error category has specific recovery suggestions
3. **Comprehensive Tracking**: All errors are logged with unique IDs and full context
4. **Graceful Degradation**: Most errors are marked as recoverable with fallback strategies

## Related Components

- `services/error_categorizer.py`: Service for categorizing exceptions into ErrorEvents
- `services/test_error_categorizer.py`: Comprehensive unit tests (26 tests)
- `services/error_categorizer_demo.py`: Demo script showing usage examples

## Requirements Satisfied

This implementation satisfies the following requirements from the production-resilience spec:

- **Requirement 14.1**: Error categorization into standardized types
- **Requirement 14.2**: Structured error logging with metadata
- **Requirement 14.6**: Error recovery suggestions
- **Requirement 20.1**: Professional error messaging
- **Requirement 20.2**: User-friendly translations of technical errors
