"""
Error categorization models for Lead Autopilot.

Defines error categories, error events, and structured error tracking
for comprehensive monitoring and user-friendly error messaging.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    """Standardized error categories for monitoring and reporting."""
    
    INPUT_VALIDATION = "input_validation"
    SCRAPING_BLOCKED = "scraping_blocked"
    SCRAPING_TIMEOUT = "scraping_timeout"
    AI_TIMEOUT = "ai_timeout"
    AI_INVALID_RESPONSE = "ai_invalid_response"
    PDF_RENDERING = "pdf_rendering"
    EMAIL_SMTP = "email_smtp"
    API_RATE_LIMIT = "api_rate_limit"
    API_UNAVAILABLE = "api_unavailable"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    UNKNOWN = "unknown"


class ErrorEvent(BaseModel):
    """Structured error event for logging and monitoring."""
    
    error_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    lead_id: str
    category: ErrorCategory
    component: str = Field(..., description="Component name (e.g., 'scraper', 'ai_analyzer', 'pdf_generator')")
    message: str = Field(..., description="Technical error message for internal logging")
    technical_details: Optional[str] = Field(default=None, description="Full exception traceback or additional context")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retry_attempt: int = Field(default=0, ge=0, description="Current retry attempt number")
    recoverable: bool = Field(default=True, description="Whether the error can be recovered from")
    recovery_action: Optional[str] = Field(default=None, description="Suggested recovery action")
    user_facing_message: str = Field(default="", description="Professional message for end users")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error_id": "a1b2c3d4",
                "lead_id": "lead_123456",
                "category": "scraping_blocked",
                "component": "scraper",
                "message": "HTTP 403 Forbidden",
                "technical_details": "Firecrawl API returned 403 for https://example.com",
                "timestamp": "2024-01-15T10:30:00Z",
                "retry_attempt": 1,
                "recoverable": True,
                "recovery_action": "Fallback to basic scraper",
                "user_facing_message": "We encountered difficulty accessing the website. Using alternative data collection method."
            }
        }
        }
