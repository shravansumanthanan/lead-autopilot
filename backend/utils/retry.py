"""
Retry Utilities.

Provides a robust async retry decorator with exponential backoff, jitter,
and support for Retry-After headers and non-retryable exceptions.
"""

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, Any, TypeVar, Tuple, Type, Optional, Set, Dict

logger = logging.getLogger(__name__)

T = TypeVar("T")

class RetryException(Exception):
    """Base exception for retry logic."""
    pass

class NonRetryableError(RetryException):
    """Wrap an exception that should not be retried."""
    pass

class RetryEngine:
    """Configurable engine for executing operations with retries."""
    
    def __init__(
        self,
        retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        non_retryable_exceptions: Tuple[Type[Exception], ...] = (),
    ):
        self.retries = retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.non_retryable_exceptions = non_retryable_exceptions
        
    def _calculate_delay(self, attempt: int, error: Exception) -> float:
        """Calculate delay with exponential backoff and jitter, respecting Retry-After."""
        # Check for Retry-After header
        retry_after = self._extract_retry_after(error)
        if retry_after is not None:
            return retry_after
            
        # Exponential backoff
        delay = self.base_delay * (2 ** (attempt - 1))
        
        # Add jitter
        if self.jitter:
            # Full jitter: delay = random between 0 and exponential_delay
            delay = random.uniform(0, delay)
            
        return min(delay, self.max_delay)

    def _extract_retry_after(self, error: Exception) -> Optional[float]:
        """Extract Retry-After header from an exception if present."""
        # Support for httpx.HTTPStatusError or similar exceptions
        response = getattr(error, 'response', None)
        if response and hasattr(response, 'headers'):
            headers = getattr(response, 'headers', {})
            retry_after = headers.get('Retry-After') or headers.get('retry-after')
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        return None

    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        if isinstance(error, self.non_retryable_exceptions) or isinstance(error, NonRetryableError):
            return False
        if isinstance(error, self.retryable_exceptions):
            return True
        return False

    async def execute(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function with retries."""
        last_exception = None
        
        for attempt in range(1, self.retries + 2):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e) or attempt > self.retries:
                    break
                    
                delay = self._calculate_delay(attempt, e)
                
                logger.warning(
                    f"[{func.__name__}] Attempt {attempt} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
                
        if isinstance(last_exception, NonRetryableError):
            raise getattr(last_exception, "__cause__", None) or (last_exception.args[0] if getattr(last_exception, "args", None) and isinstance(last_exception.args[0], Exception) else last_exception)
        raise last_exception

def with_retry(
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()
) -> Callable:
    """
    Decorator for retrying a function using the RetryEngine.
    """
    engine = RetryEngine(
        retries=retries,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions
    )
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await engine.execute(func, *args, **kwargs)
        return wrapper
    return decorator

