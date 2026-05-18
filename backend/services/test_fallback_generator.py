import pytest
from services.fallback_generator import FallbackContentGenerator
from core_models import ScrapedData

pytestmark = pytest.mark.asyncio

def test_fallback_generator_initialization():
    generator = FallbackContentGenerator()
    assert getattr(generator, "templates", None) is not None
    assert "technology" in generator.templates
    assert "default" in generator.templates

def test_generate_industry_template_selection():
    generator = FallbackContentGenerator()
    
    # Exact match via substring
    tech_template = generator._get_industry_template("Technology Services")
    assert "Cloud transitions" in tech_template["opportunities"]
    
    # Non-existent matching should fallback to default
    unknown_template = generator._get_industry_template("Space Exploration")
    assert "Digital transformation" in unknown_template["opportunities"]
    
    # Empty string should fallback to default
    empty_template = generator._get_industry_template("")
    assert empty_template == unknown_template

def test_generate_executive_summary():
    generator = FallbackContentGenerator()
    scraped = ScrapedData(title="Acme Corp Services", hero_text="We make great widgets.")
    
    exec_summary = generator.generate_executive_summary("Acme", "Manufacturing", scraped)
    
    assert "Acme" in exec_summary
    assert "Manufacturing" in exec_summary
    assert "Acme Corp Services" in exec_summary
    assert len(exec_summary) >= 50

def test_generate_fallback_analysis():
    generator = FallbackContentGenerator()
    scraped = ScrapedData()
    
    analysis = generator.generate_fallback_analysis("FinanceOrg", "finance", scraped)
    
    assert len(analysis.executive_summary) >= 50
    assert len(analysis.current_state_assessment) >= 50
    assert len(analysis.action_roadmap) >= 2
    assert analysis.action_roadmap[0].recommendation == "Modernize Digital Banking"
    assert "Fintech partnerships" in analysis.swot.opportunities
    assert len(analysis.strategic_opportunities) >= 2
    assert len(analysis.risk_areas) >= 2
