"""
Enrichment Pipeline Module.

Orchestrates the complete data enrichment flow:
1. Scrape company website (ResilientScraperService)
2. Web search for public context (Serper.dev, optional)
3. Analyze with AI (Qwen via OpenRouter)
4. Merge and score the combined data
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core_models import AIAnalysis, EnrichedCompanyData, LeadSubmission, ScrapedData
from services.resilient_scraper import ResilientScraperService
from services.web_search import search_company_info, format_search_context
from services.resilient_ai_analysis import ResilientAIAnalysisService
from services.quality_scorer import QualityScoreCalculator
from utils.validation import is_valid_url, normalize_url
from models.errors import ErrorCategory, ErrorEvent

logger = logging.getLogger(__name__)

# Initialize singletons
scraper_service = ResilientScraperService()
ai_service = ResilientAIAnalysisService()
quality_calculator = QualityScoreCalculator()

async def run_enrichment_pipeline(lead: LeadSubmission) -> EnrichedCompanyData:
    """
    Run the complete enrichment pipeline for a lead submission.
    """
    logger.info(f"Starting enrichment pipeline for {lead.company} ({lead.website})")

    # ── Step 1: Scrape Website ───────────────────────────────────────
    scraped = ScrapedData()
    scraper_warnings = []
    
    is_valid = is_valid_url(str(lead.website))
    
    if not is_valid:
        logger.warning(f"Missing or invalid URL for {lead.company}. Gracefully degrading.")
        scraper_warnings.append(f"Invalid URL: {lead.website}")
    else:
        normalized_url = normalize_url(str(lead.website))
        logger.info(f"Using normalized URL: {normalized_url}")
        
        try:
            scraped, scraper_warnings = await scraper_service.scrape_with_fallbacks(normalized_url)
            logger.info(f"Scraping completed with {len(scraper_warnings)} warnings.")
        except Exception as e:
            logger.error(f"Absolute scraping failure for {normalized_url}: {e}")
            scraper_warnings.append(str(e))

    # ── Step 2: Web Search (Optional) ────────────────────────────────
    search_results = {}
    search_context = ""
    try:
        search_results = await search_company_info(lead.company, lead.industry)
        if search_results:
            search_context = format_search_context(search_results)
            logger.info(f"Web search context gathered for {lead.company} ({len(search_context)} chars)")
    except Exception as e:
        logger.warning(f"Web search failed for {lead.company}: {e}")

    # ── Step 3: AI Analysis ──────────────────────────────────────────
    ai_warnings = []
    try:
        analysis, ai_warnings = await ai_service.analyze_with_validation(
            company_name=lead.company,
            industry=lead.industry,
            website_url=str(lead.website),
            scraped=scraped,
            prospect_message=lead.message or "",
            web_search_context=search_context,
        )
        logger.info(f"AI analysis complete for {lead.company} with {len(ai_warnings)} warnings")
    except Exception as e:
        logger.error(f"Absolute AI analysis failure for {lead.company}: {e}")
        analysis = AIAnalysis()  # Final safety fallback though resilient service should handle this
        ai_warnings.append(str(e))

    # ── Step 4: Calculate Quality & Assemble ─────────────────────────
    # Use the new QualityScoreCalculator
    scraped_dict = scraped.model_dump() if hasattr(scraped, "model_dump") else scraped.dict()
    analysis_dict = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict()
    
    quality_components = quality_calculator.calculate_score(
        scraped_data=scraped_dict,
        ai_analysis=analysis_dict,
        web_search_data=search_results
    )
    
    # Generate Confidence Indicators
    if quality_components.composite_score >= 0.8:
        confidence_level = "High"
        confidence_reason = "Comprehensive public data was retrieved successfully."
    elif quality_components.composite_score >= 0.4:
        confidence_level = "Medium"
        confidence_reason = "Limited publicly accessible website content was available for deep technical assessment."
    else:
        confidence_level = "Low"
        confidence_reason = "The system gracefully degraded due to missing data or blocked requests."

    logger.info(f"Enrichment quality score for {lead.company}: {quality_components.composite_score:.2f} ({confidence_level})")

    # Optional: We could log the warnings as ErrorEvents. For now they're just strings.
    # In a real app we'd probably save these ErrorEvents to the DB.
    
    enriched = EnrichedCompanyData(
        lead=lead,
        scraped=scraped,
        analysis=analysis,
        enriched_at=datetime.now(timezone.utc),
        data_quality_score=quality_components.composite_score,
        confidence_level=confidence_level,
        confidence_reason=confidence_reason,
        errors=[],
        warnings=scraper_warnings + ai_warnings,
    )
    
    # Storing warnings on the model? EnrichedCompanyData doesn't have a place for them currently, 
    # but the task asks to "handle warnings, store errors, and update quality score".
    # I will add an `errors: List[str] = []` field to `EnrichedCompanyData` later if needed,
    # or I will just pass it to the db if this returns it.

    logger.info(f"Enrichment pipeline complete for {lead.company}")
    return enriched
