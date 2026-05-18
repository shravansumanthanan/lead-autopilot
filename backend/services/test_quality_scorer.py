import pytest
from services.quality_scorer import QualityScoreCalculator

def test_weights_sum_to_one():
    calc = QualityScoreCalculator()
    assert sum(calc.WEIGHTS.values()) == 1.0

def test_score_scraped_data_empty():
    calc = QualityScoreCalculator()
    assert calc._score_scraped_data({}) == 0.0

def test_score_scraped_data_partial():
    calc = QualityScoreCalculator()
    data = {"title": "Test", "meta_description": "A description"}
    assert calc._score_scraped_data(data) == 0.2

def test_score_scraped_data_full():
    calc = QualityScoreCalculator()
    data = {
        "title": "Test",
        "hero_text": "Hero",
        "services": ["S1"],
        "social_links": {"twitter": "link"}
    }
    assert calc._score_scraped_data(data) == 1.0

def test_score_ai_analysis_empty():
    calc = QualityScoreCalculator()
    assert calc._score_ai_analysis({}) == 0.0

def test_score_ai_analysis_partial():
    calc = QualityScoreCalculator()
    data = {"executive_summary": "Test summary", "action_roadmap": []}
    assert calc._score_ai_analysis(data) == 0.3

def test_score_ai_analysis_full():
    calc = QualityScoreCalculator()
    data = {
        "executive_summary": "Summary",
        "swot": {"strengths": ["S1"]},
        "action_roadmap": [{"id": 1}],
        "scorecard": {"seo": 80}
    }
    assert calc._score_ai_analysis(data) == 1.0

def test_score_web_search_empty():
    calc = QualityScoreCalculator()
    assert calc._score_web_search({}) == 0.0

def test_score_web_search_full():
    calc = QualityScoreCalculator()
    data = {
        "competitors": ["C1"],
        "news": ["N1"],
        "industry_trends": ["T1"]
    }
    assert calc._score_web_search(data) == 1.0

def test_calculate_score_composite():
    calc = QualityScoreCalculator()
    
    # Half useful scraped data -> 0.6 score (* 0.5 = 0.3)
    # Full AI -> 1.0 score (* 0.35 = 0.35)
    # Empty web search -> 0.0 (* 0.15 = 0.0)
    # Total composite = 0.65
    
    components = calc.calculate_score(
        scraped_data={"title": "T", "hero_text": "H"}, # 0.2 + 0.4 = 0.6
        ai_analysis={"executive_summary": "S", "swot": {"s": ["s1"]}, "action_roadmap": [{"1":"1"}], "scorecard": {"a": 1}},
        web_search_data=None
    )
    
    assert components.scraped_data_score == 0.6
    assert components.ai_analysis_score == 1.0
    assert components.web_search_score == 0.0
    assert components.composite_score == 0.65

def test_calculate_score_all_empty():
    calc = QualityScoreCalculator()
    comp = calc.calculate_score()
    assert comp.composite_score == 0.0
