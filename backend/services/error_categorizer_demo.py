"""
Demo script for the Error Categorization System.

This script demonstrates how to use the ErrorCategorizerService
to categorize errors and generate user-friendly messages.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.error_categorizer import ErrorCategorizerService
from models.errors import ErrorCategory


def demo_error_categorization():
    """Demonstrate error categorization with various scenarios."""
    
    service = ErrorCategorizerService()
    lead_id = "demo_lead_12345"
    
    print("=" * 80)
    print("Error Categorization System Demo")
    print("=" * 80)
    print()
    
    # Scenario 1: Scraping blocked
    print("Scenario 1: Website blocks scraping (403 Forbidden)")
    print("-" * 80)
    error = Exception("HTTP 403 Forbidden - Bot detection triggered")
    event = service.categorize_and_log(error, lead_id, "scraper", retry_attempt=1)
    print(f"Category: {event.category.value}")
    print(f"Recoverable: {event.recoverable}")
    print(f"Recovery Action: {event.recovery_action}")
    print(f"User Message: {event.user_facing_message}")
    print()
    
    # Scenario 2: AI timeout
    print("Scenario 2: AI analysis times out")
    print("-" * 80)
    error = TimeoutError("AI analysis timeout after 45 seconds")
    event = service.categorize_and_log(error, lead_id, "ai_analyzer", retry_attempt=2)
    print(f"Category: {event.category.value}")
    print(f"Recoverable: {event.recoverable}")
    print(f"Recovery Action: {event.recovery_action}")
    print(f"User Message: {event.user_facing_message}")
    print()
    
    # Scenario 3: Invalid AI response
    print("Scenario 3: AI returns invalid JSON")
    print("-" * 80)
    error = ValueError("Invalid JSON schema in AI response")
    event = service.categorize_and_log(error, lead_id, "ai_analyzer")
    print(f"Category: {event.category.value}")
    print(f"Recoverable: {event.recoverable}")
    print(f"Recovery Action: {event.recovery_action}")
    print(f"User Message: {event.user_facing_message}")
    print()
    
    # Scenario 4: Rate limiting
    print("Scenario 4: API rate limit exceeded")
    print("-" * 80)
    error = Exception("HTTP 429 Too Many Requests - Retry after 60 seconds")
    event = service.categorize_and_log(error, lead_id, "scraper")
    print(f"Category: {event.category.value}")
    print(f"Recoverable: {event.recoverable}")
    print(f"Recovery Action: {event.recovery_action}")
    print(f"User Message: {event.user_facing_message}")
    print()
    
    # Scenario 5: PDF rendering failure
    print("Scenario 5: PDF rendering fails")
    print("-" * 80)
    error = Exception("WeasyPrint rendering failed - Unicode error")
    event = service.categorize_and_log(error, lead_id, "pdf_generator")
    print(f"Category: {event.category.value}")
    print(f"Recoverable: {event.recoverable}")
    print(f"Recovery Action: {event.recovery_action}")
    print(f"User Message: {event.user_facing_message}")
    print()
    
    # Scenario 6: Email delivery failure
    print("Scenario 6: Email SMTP connection fails")
    print("-" * 80)
    error = Exception("SMTP connection refused - Connection timeout")
    event = service.categorize_and_log(error, lead_id, "email_service", retry_attempt=1)
    print(f"Category: {event.category.value}")
    print(f"Recoverable: {event.recoverable}")
    print(f"Recovery Action: {event.recovery_action}")
    print(f"User Message: {event.user_facing_message}")
    print()
    
    # Show all available categories
    print("=" * 80)
    print("All Available Error Categories")
    print("=" * 80)
    for category in ErrorCategory:
        print(f"\n{category.value}:")
        print(f"  User Message: {service.get_user_message(category)}")
        print(f"  Recovery Action: {service.get_recovery_action(category)}")
    print()
    
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    demo_error_categorization()
