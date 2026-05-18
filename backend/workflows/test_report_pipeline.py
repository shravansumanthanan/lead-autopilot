import pytest
from unittest.mock import patch, AsyncMock
from core_models import LeadSubmission, ScrapedData, AIAnalysis, EnrichedCompanyData
from workflows.report_pipeline import run_enrichment_pipeline

@pytest.fixture
def mock_lead():
    return LeadSubmission(
        company="Test Corp",
        website="https://testcorp.com",
        industry="Technology",
        name="Test User",
        email="test@testcorp.com"
    )

@pytest.mark.asyncio
async def test_run_enrichment_pipeline_success(mock_lead):
    mock_scraped = ScrapedData(title="Test", meta_description="Desc", about_text="About us")
    mock_analysis = AIAnalysis(executive_summary="This is a summary that is sufficiently long, exceeding the fifty character minimum requirement.", swot={"strengths": ["Good stuff", "and more good stuff"]}, current_state_assessment="This is another sufficiently long field exceeding fifty characters.")
    
    with patch("workflows.report_pipeline.scraper_service.scrape_with_fallbacks", new_callable=AsyncMock) as mock_scrape, \
         patch("workflows.report_pipeline.search_company_info", new_callable=AsyncMock) as mock_search, \
         patch("workflows.report_pipeline.ai_service.analyze_with_validation", new_callable=AsyncMock) as mock_analyze:
        
        mock_scrape.return_value = (mock_scraped, ["Some warning"])
        mock_search.return_value = {"competitors": ["Comp1"]}
        mock_analyze.return_value = (mock_analysis, ['AI Warning'])
        
        result = await run_enrichment_pipeline(mock_lead)
        
        assert isinstance(result, EnrichedCompanyData)
        assert result.data_quality_score > 0.0
        assert "Some warning" in result.warnings
        assert result.scraped.title == "Test"

@pytest.mark.asyncio
async def test_run_enrichment_pipeline_invalid_url(mock_lead):
    mock_lead.website = "invalid-url"
    
    with patch("workflows.report_pipeline.scraper_service.scrape_with_fallbacks", new_callable=AsyncMock) as mock_scrape, \
         patch("workflows.report_pipeline.search_company_info", new_callable=AsyncMock) as mock_search, \
         patch("workflows.report_pipeline.ai_service.analyze_with_validation", new_callable=AsyncMock) as mock_analyze:
        
        mock_search.return_value = {}
        mock_analyze.return_value = (AIAnalysis(), [])
        
        result = await run_enrichment_pipeline(mock_lead)
        
        mock_scrape.assert_not_called()
        assert any("Invalid URL" in w for w in result.warnings)
        assert result.confidence_level == "Low"

@pytest.mark.asyncio
async def test_run_enrichment_pipeline_scraping_failure(mock_lead):
    with patch("workflows.report_pipeline.scraper_service.scrape_with_fallbacks", new_callable=AsyncMock) as mock_scrape, \
         patch("workflows.report_pipeline.search_company_info", new_callable=AsyncMock) as mock_search, \
         patch("workflows.report_pipeline.ai_service.analyze_with_validation", new_callable=AsyncMock) as mock_analyze:
        
        mock_scrape.side_effect = Exception("Total scraping failure")
        mock_search.return_value = {}
        mock_analyze.return_value = (AIAnalysis(), [])
        
        result = await run_enrichment_pipeline(mock_lead)
        
        assert any("Total scraping failure" in w for w in result.warnings)
        assert result.confidence_level == "Low"

@pytest.mark.asyncio
async def test_run_enrichment_pipeline_ai_failure(mock_lead):
    mock_scraped = ScrapedData(title="Test AI Fail")
    
    with patch("workflows.report_pipeline.scraper_service.scrape_with_fallbacks", new_callable=AsyncMock) as mock_scrape, \
         patch("workflows.report_pipeline.search_company_info", new_callable=AsyncMock) as mock_search, \
         patch("workflows.report_pipeline.ai_service.analyze_with_validation", new_callable=AsyncMock) as mock_analyze:
        
        mock_scrape.return_value = (mock_scraped, [])
        mock_search.return_value = {}
        
        # Simulate AI analysis raising an unhandled exception 
        # (Though analyze_with_validation normally catches it, we test the absolute fallback here)
        mock_analyze.side_effect = Exception("Major AI Outage")
        
        result = await run_enrichment_pipeline(mock_lead)
        
        assert any("Absolute AI analysis failure" in w or "Major AI Outage" in w for w in result.warnings)
        # It should still succeed gracefully
        assert isinstance(result, EnrichedCompanyData)
