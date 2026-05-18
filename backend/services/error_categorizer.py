"""
Error categorization service for Lead Autopilot.

Provides intelligent error categorization, user-friendly message generation,
and recovery action suggestions for comprehensive error handling.
"""

from __future__ import annotations

import logging
from typing import Optional

# Handle imports for both direct execution and module import
try:
    from backend.models.errors import ErrorCategory, ErrorEvent
except ImportError:
    from models.errors import ErrorCategory, ErrorEvent


logger = logging.getLogger("lead-autopilot.errors")


class ErrorCategorizerService:
    """
    Categorizes errors and generates user-friendly messages with recovery actions.
    
    This service translates technical errors into structured ErrorEvent objects
    with appropriate categories, professional user-facing messages, and actionable
    recovery suggestions.
    """
    
    # User-friendly messages for each error category
    USER_MESSAGES = {
        ErrorCategory.INPUT_VALIDATION: "The information provided needs adjustment. Please verify and try again.",
        ErrorCategory.SCRAPING_BLOCKED: "We encountered difficulty accessing the website. Using alternative data collection methods.",
        ErrorCategory.SCRAPING_TIMEOUT: "The website took too long to respond. We'll use available information to proceed.",
        ErrorCategory.AI_TIMEOUT: "Our analysis service is experiencing delays. Generating a simplified report.",
        ErrorCategory.AI_INVALID_RESPONSE: "We received unexpected data from our analysis service. Using fallback analysis.",
        ErrorCategory.PDF_RENDERING: "Report formatting encountered an issue. Delivering in an alternative format.",
        ErrorCategory.EMAIL_SMTP: "Email delivery is temporarily delayed. We'll retry shortly.",
        ErrorCategory.API_RATE_LIMIT: "We're experiencing high demand. Your request will be processed momentarily.",
        ErrorCategory.API_UNAVAILABLE: "An external service is temporarily unavailable. Using cached or alternative data.",
        ErrorCategory.CIRCUIT_BREAKER_OPEN: "A service is temporarily disabled for maintenance. Using fallback methods.",
        ErrorCategory.UNKNOWN: "An unexpected issue occurred. Our team has been notified and we're working to resolve it.",
    }
    
    # Recovery action suggestions for each error category
    RECOVERY_ACTIONS = {
        ErrorCategory.INPUT_VALIDATION: "Validate and normalize input, proceed with warnings",
        ErrorCategory.SCRAPING_BLOCKED: "Fallback to basic scraper or metadata-only extraction",
        ErrorCategory.SCRAPING_TIMEOUT: "Retry with shorter timeout or skip to AI analysis",
        ErrorCategory.AI_TIMEOUT: "Retry with exponential backoff or use fallback content generator",
        ErrorCategory.AI_INVALID_RESPONSE: "Retry with schema examples or generate fallback analysis",
        ErrorCategory.PDF_RENDERING: "Retry with simplified template or generate markdown report",
        ErrorCategory.EMAIL_SMTP: "Retry with exponential backoff (3 attempts)",
        ErrorCategory.API_RATE_LIMIT: "Wait for Retry-After duration and retry",
        ErrorCategory.API_UNAVAILABLE: "Open circuit breaker and use fallback data sources",
        ErrorCategory.CIRCUIT_BREAKER_OPEN: "Use cached data or fallback content generator",
        ErrorCategory.UNKNOWN: "Log full traceback and proceed with graceful degradation",
    }
    
    def __init__(self):
        """Initialize the error categorizer service."""
        self.logger = logger
    
    def categorize_and_log(
        self,
        error: Exception,
        lead_id: str,
        component: str,
        retry_attempt: int = 0,
        additional_context: Optional[str] = None
    ) -> ErrorEvent:
        """
        Categorize an exception and create a structured ErrorEvent.
        
        Args:
            error: The exception that occurred
            lead_id: The lead ID associated with this error
            component: The component where the error occurred (e.g., 'scraper', 'ai_analyzer')
            retry_attempt: Current retry attempt number
            additional_context: Optional additional context about the error
        
        Returns:
            ErrorEvent: Structured error event with category, messages, and recovery actions
        """
        category = self._categorize_error(error, component)
        
        error_event = ErrorEvent(
            lead_id=lead_id,
            category=category,
            component=component,
            message=str(error),
            technical_details=self._format_technical_details(error, additional_context),
            retry_attempt=retry_attempt,
            recoverable=self._is_recoverable(category),
            recovery_action=self.RECOVERY_ACTIONS.get(category),
            user_facing_message=self.USER_MESSAGES.get(category, self.USER_MESSAGES[ErrorCategory.UNKNOWN])
        )
        
        # Log the error event
        self._log_error_event(error_event)
        
        return error_event
    
    def _categorize_error(self, error: Exception, component: str) -> ErrorCategory:
        """
        Determine the error category based on exception type and component.
        
        Args:
            error: The exception to categorize
            component: The component where the error occurred
        
        Returns:
            ErrorCategory: The appropriate error category
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Input validation errors
        if component == "validator" or "validation" in error_str:
            return ErrorCategory.INPUT_VALIDATION
        
        # Scraping errors
        if component == "scraper":
            if "403" in error_str or "forbidden" in error_str or "blocked" in error_str:
                return ErrorCategory.SCRAPING_BLOCKED
            if "timeout" in error_str or error_type in ("TimeoutError", "asyncio.TimeoutError"):
                return ErrorCategory.SCRAPING_TIMEOUT
            if "429" in error_str or "rate limit" in error_str:
                return ErrorCategory.API_RATE_LIMIT
            if "503" in error_str or "unavailable" in error_str or "connection" in error_str:
                return ErrorCategory.API_UNAVAILABLE
        
        # AI analysis errors
        if component == "ai_analyzer":
            if "timeout" in error_str or error_type in ("TimeoutError", "asyncio.TimeoutError"):
                return ErrorCategory.AI_TIMEOUT
            if "json" in error_str or "schema" in error_str or "validation" in error_str:
                return ErrorCategory.AI_INVALID_RESPONSE
            if "429" in error_str or "rate limit" in error_str:
                return ErrorCategory.API_RATE_LIMIT
            if "503" in error_str or "unavailable" in error_str or "connection" in error_str:
                return ErrorCategory.API_UNAVAILABLE
        
        # PDF generation errors
        if component == "pdf_generator":
            return ErrorCategory.PDF_RENDERING
        
        # Email errors
        if component == "email_service":
            return ErrorCategory.EMAIL_SMTP
        
        # Circuit breaker errors
        if "circuit breaker" in error_str or "breaker open" in error_str:
            return ErrorCategory.CIRCUIT_BREAKER_OPEN
        
        # Rate limiting (general)
        if "429" in error_str or "rate limit" in error_str:
            return ErrorCategory.API_RATE_LIMIT
        
        # Service unavailability (general)
        if "503" in error_str or "unavailable" in error_str or "connection" in error_str:
            return ErrorCategory.API_UNAVAILABLE
        
        # Default to unknown
        return ErrorCategory.UNKNOWN
    
    def _is_recoverable(self, category: ErrorCategory) -> bool:
        """
        Determine if an error category is recoverable.
        
        Args:
            category: The error category
        
        Returns:
            bool: True if the error is recoverable, False otherwise
        """
        # Most errors are recoverable through fallbacks
        non_recoverable = {
            ErrorCategory.INPUT_VALIDATION,  # May need user correction
        }
        return category not in non_recoverable
    
    def _format_technical_details(
        self,
        error: Exception,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Format technical details for internal logging.
        
        Args:
            error: The exception
            additional_context: Optional additional context
        
        Returns:
            str: Formatted technical details
        """
        details = f"{type(error).__name__}: {str(error)}"
        if additional_context:
            details += f"\nContext: {additional_context}"
        return details
    
    def _log_error_event(self, error_event: ErrorEvent) -> None:
        """
        Log the error event with appropriate severity.
        
        Args:
            error_event: The error event to log
        """
        log_message = (
            f"[{error_event.error_id}] {error_event.category.value} in {error_event.component} "
            f"(lead: {error_event.lead_id}, attempt: {error_event.retry_attempt}): "
            f"{error_event.message}"
        )
        
        # Log with appropriate level based on recoverability
        if error_event.recoverable:
            self.logger.warning(log_message)
            if error_event.recovery_action:
                self.logger.info(f"[{error_event.error_id}] Recovery action: {error_event.recovery_action}")
        else:
            self.logger.error(log_message)
        
        # Log technical details at debug level
        if error_event.technical_details:
            self.logger.debug(f"[{error_event.error_id}] Technical details: {error_event.technical_details}")
    
    def get_user_message(self, category: ErrorCategory) -> str:
        """
        Get the user-friendly message for an error category.
        
        Args:
            category: The error category
        
        Returns:
            str: User-friendly error message
        """
        return self.USER_MESSAGES.get(category, self.USER_MESSAGES[ErrorCategory.UNKNOWN])
    
    def get_recovery_action(self, category: ErrorCategory) -> Optional[str]:
        """
        Get the recovery action suggestion for an error category.
        
        Args:
            category: The error category
        
        Returns:
            Optional[str]: Recovery action suggestion, or None if not available
        """
        return self.RECOVERY_ACTIONS.get(category)
