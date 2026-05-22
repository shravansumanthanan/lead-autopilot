import pytest
from datetime import datetime
from core_models import EnrichedCompanyData, LeadSubmission, AIAnalysis, ActionItem, ScrapedData
from backend.services.markdown_generator import MarkdownReportGenerator

def test_generate_markdown_report():
    lead = LeadSubmission(
        company="Test Corp",
        website="https://testcorp.com",
        industry="Tech",
        name="Test User",
        email="test@testcorp.com"
    )
    scraped = ScrapedData(title="Test", meta_description="Desc")
    analysis = AIAnalysis(
        executive_summary="This is the exec summary that needs to be longer and surely is enough to exceed the minimum threshold requirements set explicitly in core models.",
        current_state_assessment="This is the current state that needs to be longer and surely is enough to exceed the minimum threshold requirements set explicitly in core models.",
        swot={
             "strengths": ["Strong engineering"],
             "weaknesses": ["Slow marketing"]
        },
        action_roadmap=[
            ActionItem(recommendation="Scale", timeline="Q1", effort="Low", impact="High"),
            ActionItem(recommendation="Wait", timeline="Q2", effort="Low", impact="Low")
        ]
    )
    data = EnrichedCompanyData(
        lead=lead,
        scraped=scraped,
        analysis=analysis,
        enriched_at=datetime(2023, 1, 1, 12, 0, 0),
        data_quality_score=0.95,
        confidence_level="High",
        confidence_reason="Because",
        warnings=[],
        errors=[]
    )
    
    generator = MarkdownReportGenerator()
    report = generator.generate_markdown_report(data)
    
    assert "Test Corp" in report
    assert "2023-01-01 12:00:00 UTC" in report
    assert "0.95" in report
    assert "High" in report
    assert "This is the exec summary" in report
    assert "Strong engineering" in report
    assert "Scale" in report
    assert "| Scale | Q1 | Low | High |" in report
