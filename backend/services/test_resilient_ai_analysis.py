import pytest
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError

from core_models import ScrapedData, AIAnalysis, ActionItem
from services.resilient_ai_analysis import ResilientAIAnalysisService, AIAnalysisError
from utils.circuit_breaker import _circuit_breakers

pytestmark = pytest.mark.asyncio

@pytest.fixture
def service():
    _circuit_breakers.clear()
    return ResilientAIAnalysisService()

async def test_analyze_success(service):
    scraped = ScrapedData(title="Tech Corp")
    valid_json_response = """
    {
        "executive_summary": "This is a sufficiently long summary for testing purposes that exceeds fifty characters.",
        "current_state_assessment": "This is also a sufficiently long assessment that will correctly pass the length validations.",
        "swot": {
            "strengths": ["Strong AI tech"]
        },
        "action_roadmap": [
            {"title": "Upgrade DB", "description": "Needs scaling.", "priority": "High"},
            {"title": "Implement caching", "description": "Reduce loads.", "priority": "Medium"}
        ],
        "key_findings": [],
        "risk_areas": ["Data loss", "Scaling caps"],
        "strategic_opportunities": ["New Markets", "B2B expansion"],
        "scorecard": {}
    }
    """
    
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content=valid_json_response))]
    
    with patch("services.resilient_ai_analysis._get_client") as mock_client:
        mock_chat = AsyncMock()
        mock_chat.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_chat
        
        analysis, warnings = await service.analyze_with_validation(
            "Tech Corp", "Technology", "https://tech.com", scraped
        )
        
        assert len(warnings) == 0
        assert analysis.executive_summary.startswith("This is a sufficiently")
        assert len(analysis.action_roadmap) == 2

async def test_fallback_on_json_failure(service):
    scraped = ScrapedData(title="Fail Corp")
    
    with patch("services.resilient_ai_analysis._get_client", autospec=True) as mock_client:
        mock_chat = AsyncMock()
        # Mock completion to throw an exception
        mock_chat.chat.completions.create.side_effect = Exception("OpenRouter is down")
        mock_client.return_value = mock_chat
        
        analysis, warnings = await service.analyze_with_validation(
            "Fail Corp", "Finance", "https://fail.com", scraped
        )
        
        assert len(warnings) > 0
        assert any("AI Service failed" in w or "circuit breaker" in w for w in warnings)
        
        # Verify FallbackContentGenerator took over
        assert "Finance" in analysis.executive_summary or "Fail Corp" in analysis.executive_summary
        assert analysis.action_roadmap[0].recommendation == "Modernize Digital Banking"

async def test_repetitive_loop_hallucination_triggers_fallback(service):
    scraped = ScrapedData()
    hallucination_response = """
    {
        "executive_summary": "We do good stuff. We do good stuff. We do good stuff. We do good stuff.",
        "current_state_assessment": "The company is growing. The company is growing. The company is growing.",
        "swot": {},
        "action_roadmap": [
            {"title": "Upgrade DB", "description": "Needs scaling.", "priority": "High"},
            {"title": "Implement caching", "description": "Reduce loads.", "priority": "Medium"}
        ],
        "key_findings": [],
        "risk_areas": ["Data loss", "Scaling caps"],
        "strategic_opportunities": ["New Markets", "B2B expansion"],
        "scorecard": {}
    }
    """
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content=hallucination_response))]
    
    with patch("services.resilient_ai_analysis._get_client") as mock_client:
        mock_chat = AsyncMock()
        mock_chat.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_chat
        
        analysis, warnings = await service.analyze_with_validation(
            "Loop Corp", "Retail", "https://loop.com", scraped
        )
        
        # Service fails because loop detection triggers exception, caught by wrap and returns fallback
        assert len(warnings) > 0
        assert any("AI Service failed: Repetitive content loop" in w for w in warnings)
        assert analysis.action_roadmap[0].recommendation == "Unify Omnichannel Experience"
        
