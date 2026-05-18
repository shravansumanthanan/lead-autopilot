import pytest
from pydantic import ValidationError
from core_models import AIAnalysis, ActionItem, SWOTAnalysis

pytestmark = pytest.mark.asyncio

def test_ai_analysis_validation_success():
    analysis = AIAnalysis(
        executive_summary="This is a sufficiently long summary for testing purposes that definitely exceeds the fifty character limit.",
        current_state_assessment="This is also a properly lengthy string to satisfy requirements and make sure all validators pass cleanly.",
        action_roadmap=[
            ActionItem(title="Do this", description="Like this", priority="High"),
            ActionItem(title="Do that", description="Like that", priority="Medium")
        ],
        strategic_opportunities=["Opportunity 1", "Opportunity 2"],
        risk_areas=["Risk 1", "Risk 2"]
    )
    assert analysis.executive_summary.startswith("This is a")
    assert len(analysis.action_roadmap) == 2
    assert len(analysis.strategic_opportunities) == 2
    assert len(analysis.risk_areas) == 2

def test_ai_analysis_validation_failure_min_length():
    with pytest.raises(ValidationError) as exc_info:
        AIAnalysis(executive_summary="Too short summary.")
    assert "executive_summary" in str(exc_info.value)
    assert "must be at least 50 characters" in str(exc_info.value)

def test_ai_analysis_validation_failure_list_items():
    with pytest.raises(ValidationError) as exc_info:
        AIAnalysis(strategic_opportunities=["Only one opp"])
    assert "strategic_opportunities" in str(exc_info.value)
    assert "must contain at least 2 items" in str(exc_info.value)

def test_ai_analysis_validation_empty_allowed():
    # Because of default="", empty should be allowed by validators
    analysis = AIAnalysis()
    assert analysis.executive_summary == ""
    assert analysis.action_roadmap == []
