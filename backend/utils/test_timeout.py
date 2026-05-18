import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch

from backend.utils.timeout import TimeoutManager, with_timeout, timeout_manager

@pytest.mark.asyncio
async def test_execute_with_timeout_success():
    manager = TimeoutManager(default_timeout=1.0)
    mock_func = AsyncMock(return_value="success")
    
    result = await manager.execute_with_timeout(mock_func)
    
    assert result == "success"
    mock_func.assert_awaited_once()

@pytest.mark.asyncio
async def test_execute_with_timeout_fails():
    manager = TimeoutManager(default_timeout=0.01)
    
    async def slow_func():
        await asyncio.sleep(0.1)
        return "success"
        
    with pytest.raises(asyncio.TimeoutError):
        await manager.execute_with_timeout(slow_func)

@pytest.mark.asyncio
async def test_timeout_context_success():
    manager = TimeoutManager(default_timeout=1.0)
    
    async with manager.context(timeout=0.5):
        await asyncio.sleep(0.01)
        success = True
        
    assert success

@pytest.mark.asyncio
async def test_timeout_context_fails():
    manager = TimeoutManager(default_timeout=0.01)
    
    with pytest.raises(asyncio.TimeoutError):
        async with manager.context():
            await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_with_timeout_decorator():
    @with_timeout(timeout=0.01)
    async def slow_func():
        await asyncio.sleep(0.1)
        return "yes"
        
    with pytest.raises(asyncio.TimeoutError):
        await slow_func()
        
@patch.dict(os.environ, {"DEFAULT_TIMEOUT": "0.05"})
@pytest.mark.asyncio
async def test_env_var_override():
    manager = TimeoutManager(default_timeout=5.0)
    
    async def slow_func():
        await asyncio.sleep(0.1)
        return "done"
        
    with pytest.raises(asyncio.TimeoutError):
        await manager.execute_with_timeout(slow_func)
