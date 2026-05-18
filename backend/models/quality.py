from pydantic import BaseModel, Field

class QualityScoreComponents(BaseModel):
    """Breakdown of quality scores by source."""
    scraped_data_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_analysis_score: float = Field(default=0.0, ge=0.0, le=1.0)
    web_search_score: float = Field(default=0.0, ge=0.0, le=1.0)
    composite_score: float = Field(default=0.0, ge=0.0, le=1.0)


from enum import Enum

class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class ConfidenceMetadata(BaseModel):
    """Metadata regarding data confidence level and fallback rationale."""
    level: ConfidenceLevel = Field(default=ConfidenceLevel.LOW)
    reason: str = Field(default="Insufficient data available.")
    available_sources: list[str] = Field(default_factory=list)
    missing_sources: list[str] = Field(default_factory=list)

