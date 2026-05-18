import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Callable, Any, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar("T")

class TimeoutManager:
    """Manager for setting and enforcing operation timeouts."""
    
    def __init__(self, default_timeout: float = 30.0):
        # Override with environment variable if present
        env_timeout = os.getenv("DEFAULT_TIMEOUT")
        if env_timeout:
            try:
                self.default_timeout = float(env_timeout)
            except ValueError:
                self.default_timeout = default_timeout
        else:
            self.default_timeout = default_timeout

    def _get_timeout(self, override: Optional[float] = None) -> float:
        return override if override is not None else self.default_timeout

    async def execute_with_timeout(
        self, 
        func: Callable[..., Any], 
        timeout: Optional[float] = None, 
        *args, **kwargs
    ) -> Any:
        """Execute a function with a timeout."""
        actual_timeout = self._get_timeout(timeout)
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=actual_timeout)
        except asyncio.TimeoutError as e:
            logger.error(f"[{func.__name__}] Operation timed out after {actual_timeout}s")
            raise e

    @asynccontextmanager
    async def context(self, timeout: Optional[float] = None, operation_name: str = "Operation"):
        """Context manager for enforcing timeout blocks."""
        actual_timeout = self._get_timeout(timeout)
        try:
            async with asyncio.timeout(actual_timeout):
                yield
        except asyncio.TimeoutError as e:
            logger.error(f"[{operation_name}] Timed out after {actual_timeout}s")
            raise e

# Global instance for ease of use
timeout_manager = TimeoutManager()

def with_timeout(timeout: Optional[float] = None) -> Callable:
    """Decorator for wrapping an async function with a timeout."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args, **kwargs):
            return await timeout_manager.execute_with_timeout(func, timeout, *args, **kwargs)
        return wrapper
    return decorator
