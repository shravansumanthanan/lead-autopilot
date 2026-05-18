"""
Validation Utilities.

Provides functions for robust URL validation and AI schema verification.
"""

from urllib.parse import urlparse
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is structurally valid and potentially reachable.
    Handles empty, missing, or malformed strings.
    """
    if not url or not isinstance(url, str):
        return False
        
    url = url.strip()
    if not url:
        return False
        
    # Attempt to normalize if missing scheme
    if not url.startswith(("http://", "https://")):
        # If there's no dot, it's likely just a word, not a domain
        if "." not in url:
            return False
        url = "https://" + url
        
    try:
        parsed = urlparse(url)
        # Needs scheme and netloc (domain)
        return all([parsed.scheme in ("http", "https"), parsed.netloc])
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """Ensure URL has a scheme."""
    if not is_valid_url(url):
        return ""
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

def validate_schema(data: dict, model_class):
    """
    Validates a dictionary against a Pydantic model.
    Returns the instantiated model, or None if validation fails.
    """
    try:
        return model_class(**data)
    except ValidationError as e:
        logger.error(f"Schema validation failed for {model_class.__name__}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during schema validation: {e}")
        return None
