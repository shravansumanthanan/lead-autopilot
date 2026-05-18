"""
Models package for Lead Autopilot.

This package contains Pydantic models for error handling and other data structures.
"""

from .errors import ErrorCategory, ErrorEvent

__all__ = ["ErrorCategory", "ErrorEvent"]
