import pytest
from pydantic import ValidationError
from core_models import AIAnalysis, ActionItem, SWOTAnalysis, Scorecard

def test_ai_analysis_validation_success():
    analysis = AIAnalysis(
        executive_summary="This is a valid executive summary that meets the minimum length requirement.",
        current_state_assessment="This is a valid current state assessment that meets the minimum length requirement.",
        swot=SWOTAnalysis(
            strengths=["Strength 1"],
            weaknesses=["Weakness 1"],
            opportunities=["Opportunity 1"],
            threats=["Threat 1"]
        ),
        key_findings=[{"category": "SEO", "observation": "Needs work."}],
        risk_areas=["Risk 1", "Risk 2"],
        strategic_opportunities=["Opportunity 1", "Opportunity 2"],
        scorecard=Scorecard(digital_maturity=5, ai_readiness=5, seo_foundation=5),
        action_roadmap=[
            ActionItem(timeline="Immediate", recommendation="Recommendation 1", impact="High", effort="Low"),
            ActionItem(timeline="30 Days", recommendation="Recommendation 2", impact="High", effort="Medium")
        ]
    )
    assert analysis

def test_ai_analysis_validation_failure_min_length():
    with pytest.raises(ValidationError):
        AIAnalysis(
            executive_summary="Too short.",
            current_state_assessment="Too short."
        )

def test_ai_analysis_validation_failure_list_items():
    with pytest.raises(ValidationError):
        AIAnalysis(
            executive_summary="This is a valid executive summary that meets the minimum length requirement.",
            current_state_assessment="This is a valid current state assessment that meets the minimum length requirement.",
            action_roadmap=[ActionItem(timeline="Immediate", recommendation="Only one item")]
        )

def test_ai_analysis_validation_empty_allowed():
    # If the AI returns empty strings or empty lists, they should be allowed
    analysis = AIAnalysis(
        executive_summary="",
        current_state_assessment="",
        action_roadmap=[],
        strategic_opportunities=[],
        risk_areas=[]
    )
    assert analysis
