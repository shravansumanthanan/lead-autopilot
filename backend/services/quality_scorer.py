import logging
from core_models import QualityScoreComponents

logger = logging.getLogger(__name__)

class QualityScoreCalculator:
    """Calculates a composite quality score based on available data."""
    
    # Weights for each component. Must sum to 1.0
    WEIGHTS = {
        "scraped": 0.5,
        "ai": 0.35,
        "search": 0.15
    }

    def __init__(self):
        # Validate weights Configuration
        total = sum(self.WEIGHTS.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Quality weights must sum to 1.0, got {total}")

    def _score_scraped_data(self, scraped_data: dict) -> float:
        """Score based on completeness of scraped data."""
        if not scraped_data:
            return 0.0
            
        score = 0.0
        # Check title and meta
        if scraped_data.get("title") or scraped_data.get("meta_description"):
            score += 0.2
        # Check main content
        if scraped_data.get("hero_text") or scraped_data.get("about_text"):
            score += 0.4
        # Check structured lists
        if scraped_data.get("services") or scraped_data.get("tech_stack"):
            score += 0.2
        # Check contact/social metadata
        if scraped_data.get("contact_info") or scraped_data.get("social_links"):
            score += 0.2
            
        return score

    def _score_ai_analysis(self, ai_analysis: dict) -> float:
        """Score based on completeness of AI analysis."""
        if not ai_analysis:
            return 0.0
            
        score = 0.0
        # Has executive summary
        if ai_analysis.get("executive_summary"):
            score += 0.3
            
        # Has SWOT analysis
        swot = ai_analysis.get("swot", {})
        if swot and any(swot.values()):  # Some swot elements exist
            score += 0.3
            
        # Has action roadmap
        roadmap = ai_analysis.get("action_roadmap", [])
        if roadmap and len(roadmap) > 0:
            score += 0.2
            
        # Has scorecard
        scorecard = ai_analysis.get("scorecard", {})
        if scorecard and any(scorecard.values()):
            score += 0.2
            
        return score

    def _score_web_search(self, web_search_data: dict) -> float:
        """Score based on completeness of web search results."""
        if not web_search_data:
            return 0.0
            
        score = 0.0
        if web_search_data.get("organic_results"):
            score += 0.5
        if web_search_data.get("news"):
            score += 0.5
            
        return score

    def calculate_score(self, scraped_data: dict = None, ai_analysis: dict = None, web_search_data: dict = None) -> QualityScoreComponents:
        """Combine all scores into a single quality score components object."""
        scraped_score = self._score_scraped_data(scraped_data or {})
        ai_score = self._score_ai_analysis(ai_analysis or {})
        search_score = self._score_web_search(web_search_data or {})
        
        composite = (
            (scraped_score * self.WEIGHTS["scraped"]) +
            (ai_score * self.WEIGHTS["ai"]) +
            (search_score * self.WEIGHTS["search"])
        )
        
        return QualityScoreComponents(
            scraped_data_score=round(scraped_score, 2),
            ai_analysis_score=round(ai_score, 2),
            web_search_score=round(search_score, 2),
            composite_score=round(composite, 2)
        )
