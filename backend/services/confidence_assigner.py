"""
Confidence Level Assignment.

Assigns confidence levels (High/Medium/Low) based on composite quality scores
and generates human-readable explanations of data availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core_models import QualityScoreComponents


class ConfidenceLevel:
    """Confidence level constants."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class ConfidenceMetadata:
    """Structured metadata about confidence assessment."""
    level: str = ConfidenceLevel.LOW
    reason: str = ""
    available_sources: list[str] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)


class ConfidenceLevelAssigner:
    """Assigns a confidence level based on quality score and identifies data gaps."""

    # Thresholds
    HIGH_THRESHOLD = 0.8
    MEDIUM_THRESHOLD = 0.4

    def assign_confidence(self, scores: QualityScoreComponents) -> ConfidenceMetadata:
        """Assign confidence level based on total quality score."""
        level = self._determine_level(scores.composite_score)
        available = self._identify_available_sources(scores)
        missing = self._identify_missing_sources(scores)
        reason = self._generate_confidence_reason(level, available, missing)

        return ConfidenceMetadata(
            level=level,
            reason=reason,
            available_sources=available,
            missing_sources=missing,
        )

    def _determine_level(self, composite_score: float) -> str:
        if composite_score >= self.HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        elif composite_score >= self.MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def _identify_available_sources(self, scores: QualityScoreComponents) -> list[str]:
        sources = []
        if scores.scraped_data_score > 0.0:
            sources.append("scraped_data")
        if scores.ai_analysis_score > 0.0:
            sources.append("ai_analysis")
        if scores.web_search_score > 0.0:
            sources.append("web_search")
        return sources

    def _identify_missing_sources(self, scores: QualityScoreComponents) -> list[str]:
        sources = []
        if scores.scraped_data_score == 0.0:
            sources.append("scraped_data")
        if scores.ai_analysis_score == 0.0:
            sources.append("ai_analysis")
        if scores.web_search_score == 0.0:
            sources.append("web_search")
        return sources

    def _generate_confidence_reason(self, level: str, available: list[str], missing: list[str]) -> str:
        if level == ConfidenceLevel.HIGH:
            return "High confidence: Core data points and AI analysis were successfully gathered."
        elif level == ConfidenceLevel.MEDIUM:
            reasons = ["Medium confidence: Partial data available."]
            if "scraped_data" in missing:
                reasons.append("Primary website scraping failed or yielded minimal content.")
            if "ai_analysis" in missing:
                reasons.append("AI analysis could not be fully completed.")
            if "web_search" in missing:
                reasons.append("Web search yielded limited results.")
            return " ".join(reasons)
        else:
            reasons = ["Low confidence: Minimal data available."]
            if "scraped_data" in missing:
                reasons.append("Could not scrape company website.")
            if "ai_analysis" in missing:
                reasons.append("AI analysis failed or was bypassed.")
            if not available:
                reasons.append("No viable data sources were successfully queried.")
            return " ".join(reasons)
