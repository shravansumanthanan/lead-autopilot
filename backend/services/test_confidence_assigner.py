import pytest
from backend.models.quality import ConfidenceLevel, QualityScoreComponents
from backend.services.confidence_assigner import ConfidenceLevelAssigner

def test_assign_confidence_high():
    assigner = ConfidenceLevelAssigner()
    scores = QualityScoreComponents(
        scraped_data_score=1.0, 
        ai_analysis_score=1.0, 
        web_search_score=1.0,
        composite_score=0.85
    )
    meta = assigner.assign_confidence(scores)
    assert meta.level == ConfidenceLevel.HIGH
    assert meta.available_sources == ["scraped_data", "ai_analysis", "web_search"]
    assert meta.missing_sources == []

def test_assign_confidence_medium():
    assigner = ConfidenceLevelAssigner()
    scores = QualityScoreComponents(
        scraped_data_score=0.5, 
        ai_analysis_score=0.5, 
        web_search_score=0.0,
        composite_score=0.45
    )
    meta = assigner.assign_confidence(scores)
    assert meta.level == ConfidenceLevel.MEDIUM
    assert "web_search" in meta.missing_sources
    assert "scraped_data" in meta.available_sources
    assert "Medium confidence" in meta.reason

def test_assign_confidence_low():
    assigner = ConfidenceLevelAssigner()
    scores = QualityScoreComponents(
        scraped_data_score=0.0, 
        ai_analysis_score=0.0, 
        web_search_score=0.0,
        composite_score=0.0
    )
    meta = assigner.assign_confidence(scores)
    assert meta.level == ConfidenceLevel.LOW
    assert "scraped_data" in meta.missing_sources
    assert "Low confidence" in meta.reason

def test_threshold_inclusive():
    assigner = ConfidenceLevelAssigner()
    scores_high = QualityScoreComponents(composite_score=0.8)
    assert assigner.assign_confidence(scores_high).level == ConfidenceLevel.HIGH
    
    scores_med = QualityScoreComponents(composite_score=0.4)
    assert assigner.assign_confidence(scores_med).level == ConfidenceLevel.MEDIUM
    
    scores_low = QualityScoreComponents(composite_score=0.39)
    assert assigner.assign_confidence(scores_low).level == ConfidenceLevel.LOW
