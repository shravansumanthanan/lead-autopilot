import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from backend.utils.retry import RetryEngine, with_retry, NonRetryableError

class DummyHTTPError(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        if retry_after is not None:
            self.response = Mock()
            self.response.headers = {'Retry-After': str(retry_after)}

@pytest.mark.asyncio
async def test_retry_success_on_first_try():
    mock_func = AsyncMock(return_value="success")
    engine = RetryEngine(retries=3)
    result = await engine.execute(mock_func)
    
    assert result == "success"
    mock_func.assert_awaited_once()

@pytest.mark.asyncio
async def test_retry_success_after_failures():
    mock_func = AsyncMock(side_effect=[ValueError("fail 1"), ValueError("fail 2"), "success"])
    engine = RetryEngine(retries=3, base_delay=0.01, jitter=False)
    
    result = await engine.execute(mock_func)
    
    assert result == "success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_retry_max_retries_exceeded():
    mock_func = AsyncMock(side_effect=ValueError("constant failure"))
    engine = RetryEngine(retries=2, base_delay=0.01, jitter=False)
    
    with pytest.raises(ValueError):
        await engine.execute(mock_func)
        
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_non_retryable_exception():
    mock_func = AsyncMock(side_effect=TypeError("bad type"))
    engine = RetryEngine(retries=3, retryable_exceptions=(ValueError,), base_delay=0.01)
    
    with pytest.raises(TypeError):
        await engine.execute(mock_func)
        
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_non_retryable_wrapper():
    mock_func = AsyncMock(side_effect=NonRetryableError(ValueError("wrapped")))
    engine = RetryEngine(retries=3, base_delay=0.01)
    
    with pytest.raises(ValueError):
        await engine.execute(mock_func)
        
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_retry_after_header():
    mock_func = AsyncMock(side_effect=[DummyHTTPError("rate limit", retry_after=0.05), "success"])
    engine = RetryEngine(retries=3, base_delay=0.01, jitter=False)
    
    start_time = asyncio.get_event_loop().time()
    result = await engine.execute(mock_func)
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert result == "success"
    assert mock_func.call_count == 2
    assert elapsed >= 0.05

@pytest.mark.asyncio
async def test_with_retry_decorator():
    mock_func = AsyncMock(side_effect=[ValueError("fail"), "success"])
    
    @with_retry(retries=2, base_delay=0.01, jitter=False)
    async def my_func():
        return await mock_func()
        
    result = await my_func()
    assert result == "success"
    assert mock_func.call_count == 2
