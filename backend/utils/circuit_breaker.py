import asyncio
import logging
from enum import Enum
from typing import Callable, Any, TypeVar, Optional, Dict
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CircuitBreakerStateEnum(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreakerState(BaseModel):
    """Pydantic model representing circuit breaker state."""
    state: CircuitBreakerStateEnum = Field(default=CircuitBreakerStateEnum.CLOSED)
    failure_count: int = Field(default=0)
    last_failure_time: Optional[float] = Field(default=None)

class CircuitBreakerOpenError(Exception):
    """Raised when attempting to execute while the breaker is open."""
    pass

class CircuitBreakerManager:
    """Manager for circuit breaker pattern to prevent cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState()
        self._lock = None

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _get_current_time(self) -> float:
        return asyncio.get_event_loop().time()

    async def _check_state(self) -> CircuitBreakerStateEnum:
        """Evaluate and possibly update state before a call."""
        async with self.lock:
            if self.state.state == CircuitBreakerStateEnum.OPEN:
                if self.state.last_failure_time is not None:
                    elapsed = self._get_current_time() - self.state.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        logger.info("Circuit breaker transitioning from OPEN to HALF_OPEN")
                        self.state.state = CircuitBreakerStateEnum.HALF_OPEN
            return self.state.state

    async def _record_success(self):
        """Record a successful execution."""
        async with self.lock:
            if self.state.state == CircuitBreakerStateEnum.HALF_OPEN or self.state.failure_count > 0:
                logger.info(f"Circuit breaker recovered. State transitioning to CLOSED.")
                self.state.state = CircuitBreakerStateEnum.CLOSED
                self.state.failure_count = 0
                self.state.last_failure_time = None

    async def _record_failure(self):
        """Record a failed execution."""
        async with self.lock:
            self.state.failure_count += 1
            self.state.last_failure_time = self._get_current_time()
            
            if self.state.state == CircuitBreakerStateEnum.HALF_OPEN:
                logger.warning("Circuit breaker HALF_OPEN test failed. Returning to OPEN.")
                self.state.state = CircuitBreakerStateEnum.OPEN
            elif self.state.state == CircuitBreakerStateEnum.CLOSED:
                if self.state.failure_count >= self.failure_threshold:
                    logger.error(f"Circuit breaker failure threshold ({self.failure_threshold}) reached. Transitioning to OPEN.")
                    self.state.state = CircuitBreakerStateEnum.OPEN

    async def call_with_breaker(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker."""
        current_state = await self._check_state()
        
        if current_state == CircuitBreakerStateEnum.OPEN:
            raise CircuitBreakerOpenError("Circuit breaker is currently OPEN.")

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise e

    async def force_open(self):
        """Manually open the circuit breaker."""
        async with self.lock:
            logger.warning("Circuit breaker manually forced OPEN.")
            self.state.state = CircuitBreakerStateEnum.OPEN
            self.state.last_failure_time = self._get_current_time()

    async def force_close(self):
        """Manually close the circuit breaker."""
        async with self.lock:
            logger.info("Circuit breaker manually forced CLOSED.")
            self.state.state = CircuitBreakerStateEnum.CLOSED
            self.state.failure_count = 0
            self.state.last_failure_time = None


# Registry for named circuit breakers
_circuit_breakers: Dict[str, CircuitBreakerManager] = {}

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreakerManager:
    """Get or create named circuit breaker."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreakerManager(**kwargs)
    return _circuit_breakers[name]
