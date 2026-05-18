import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from backend.utils.circuit_breaker import (
    CircuitBreakerManager, 
    CircuitBreakerStateEnum, 
    CircuitBreakerOpenError,
    get_circuit_breaker
)

@pytest.fixture
def mock_time():
    with patch.object(CircuitBreakerManager, "_get_current_time", return_value=100.0) as time_mock:
        yield time_mock

@pytest.mark.asyncio
async def test_successful_call_remains_closed():
    cb = CircuitBreakerManager()
    func = AsyncMock(return_value="data")
    res = await cb.call_with_breaker(func)
    assert res == "data"
    assert cb.state.state == CircuitBreakerStateEnum.CLOSED
    assert cb.state.failure_count == 0

@pytest.mark.asyncio
async def test_failure_increases_count():
    cb = CircuitBreakerManager(failure_threshold=3)
    func = AsyncMock(side_effect=ValueError("fail"))
    with pytest.raises(ValueError):
        await cb.call_with_breaker(func)
    assert cb.state.state == CircuitBreakerStateEnum.CLOSED
    assert cb.state.failure_count == 1

@pytest.mark.asyncio
async def test_trips_to_open(mock_time):
    cb = CircuitBreakerManager(failure_threshold=2)
    func = AsyncMock(side_effect=ValueError("fail"))
    with pytest.raises(ValueError):
        await cb.call_with_breaker(func)
    with pytest.raises(ValueError):
        await cb.call_with_breaker(func)
    assert cb.state.state == CircuitBreakerStateEnum.OPEN
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call_with_breaker(AsyncMock())

@pytest.mark.asyncio
async def test_half_open_transition(mock_time):
    cb = CircuitBreakerManager(failure_threshold=1, recovery_timeout=10.0)
    func = AsyncMock(side_effect=ValueError("fail"))
    with pytest.raises(ValueError):
        await cb.call_with_breaker(func)
    assert cb.state.state == CircuitBreakerStateEnum.OPEN
    
    mock_time.return_value = 110.1
    success_func = AsyncMock(return_value="success")
    res = await cb.call_with_breaker(success_func)
    assert res == "success"
    assert cb.state.state == CircuitBreakerStateEnum.CLOSED

@pytest.mark.asyncio
async def test_half_open_failure_returns_to_open(mock_time):
    cb = CircuitBreakerManager(failure_threshold=1, recovery_timeout=10.0)
    func = AsyncMock(side_effect=ValueError("fail"))
    with pytest.raises(ValueError):
        await cb.call_with_breaker(func)
    
    mock_time.return_value = 110.1
    func2 = AsyncMock(side_effect=ValueError("fail2"))
    with pytest.raises(ValueError):
        await cb.call_with_breaker(func2)
    assert cb.state.state == CircuitBreakerStateEnum.OPEN
    
@pytest.mark.asyncio
async def test_manual_force():
    cb = CircuitBreakerManager()
    await cb.force_open()
    assert cb.state.state == CircuitBreakerStateEnum.OPEN
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call_with_breaker(AsyncMock())
    await cb.force_close()
    assert cb.state.state == CircuitBreakerStateEnum.CLOSED
    res = await cb.call_with_breaker(AsyncMock(return_value="ok"))
    assert res == "ok"

def test_registry():
    cb1 = get_circuit_breaker("service_a", failure_threshold=2)
    cb2 = get_circuit_breaker("service_a")
    cb3 = get_circuit_breaker("service_b")
    assert cb1 is cb2
    assert cb1 is not cb3
    assert cb1.failure_threshold == 2
