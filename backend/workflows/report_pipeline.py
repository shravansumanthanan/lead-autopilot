"""
Enrichment Pipeline Module.

Orchestrates the complete data enrichment flow:
1. Scrape company website (Firecrawl → BS4 fallback)
2. Web search for public context (Serper.dev, optional)
3. Analyze with AI (Qwen via OpenRouter)
4. Merge and score the combined data

Each step has graceful fallbacks — if one source fails,
others proceed with whatever data is available.
"""

from __future__ import annotations

import logging
from datetime import datetime

from core_models import AIAnalysis, EnrichedCompanyData, LeadSubmission, ScrapedData
from services.firecrawl_scraper import scrape_with_firecrawl
from services.scraper import scrape_company_website
from services.web_search import search_company_info, format_search_context
from services.ai_analysis import analyze_company
from utils.validation import is_valid_url, normalize_url

logger = logging.getLogger(__name__)


def _calculate_quality_score(scraped: ScrapedData, analysis: AIAnalysis, has_search: bool) -> float:
    """
    Calculate a data quality score (0.0 - 1.0) based on completeness.

    Scoring:
    - Scraped data fields:  0.40 max
    - AI analysis fields:   0.45 max
    - Web search context:   0.15
    """
    score = 0.0

    # Scraped data quality (0.40 max)
    if scraped.title:
        score += 0.05
    if scraped.meta_description:
        score += 0.05
    if scraped.hero_text:
        score += 0.03
    if scraped.about_text:
        score += 0.10
    if scraped.services:
        score += 0.07
    if scraped.tech_stack:
        score += 0.03
    if scraped.social_links:
        score += 0.04
    if scraped.contact_info:
        score += 0.03

    # AI analysis quality (0.45 max)
    if analysis.executive_summary and len(analysis.executive_summary) > 50:
        score += 0.12
    if analysis.swot and (analysis.swot.strengths or analysis.swot.weaknesses):
        score += 0.08
    if analysis.action_roadmap and len(analysis.action_roadmap) >= 3:
        score += 0.15
    if analysis.current_state_assessment and len(analysis.current_state_assessment) > 50:
        score += 0.10
    if analysis.key_findings:
        score += 0.05
    if analysis.risk_areas:
        score += 0.05

    # Web search bonus (0.15)
    if has_search:
        score += 0.15

    return min(score, 1.0)


async def run_enrichment_pipeline(lead: LeadSubmission) -> EnrichedCompanyData:
    """
    Run the complete enrichment pipeline for a lead submission.

    Strategy:
    1. Try Firecrawl first (better for JS-heavy sites)
    2. Fall back to HTTPX+BS4 scraper if Firecrawl unavailable/fails
    3. Run web search in parallel context gathering
    4. Feed everything to AI for analysis

    This function never raises — it always returns at least a minimal
    EnrichedCompanyData object.
    """
    logger.info(f"Starting enrichment pipeline for {lead.company} ({lead.website})")

    # ── Step 1: Scrape Website ───────────────────────────────────────
    scraped = ScrapedData()
    
    is_valid = is_valid_url(str(lead.website))
    
    if not is_valid:
        logger.warning(f"Missing or invalid URL for {lead.company}. Gracefully degrading to business-level analysis.")
    else:
        normalized_url = normalize_url(str(lead.website))
        # Try Firecrawl first (optional, JS-aware)
        try:
            firecrawl_result = await scrape_with_firecrawl(normalized_url)
            if firecrawl_result:
                scraped = firecrawl_result
                logger.info(f"Using Firecrawl data for {lead.company}")
        except Exception as e:
            logger.warning(f"Firecrawl failed for {normalized_url}: {e}")

        # Fall back to basic scraper if Firecrawl didn't provide data
        if not scraped.title and not scraped.about_text:
            try:
                scraped = await scrape_company_website(normalized_url)
                logger.info(f"Using BS4 scraper data for {lead.company}")
            except Exception as e:
                logger.error(f"Basic scraping also failed for {normalized_url}: {e}")

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
    analysis = AIAnalysis()
    try:
        analysis = await analyze_company(
            company_name=lead.company,
            industry=lead.industry,
            website_url=str(lead.website),
            scraped=scraped,
            prospect_message=lead.message,
            web_search_context=search_context,
        )
        logger.info(f"AI analysis complete for {lead.company}")
    except Exception as e:
        logger.error(f"AI analysis failed for {lead.company}: {e}")

    # ── Step 4: Calculate Quality & Assemble ─────────────────────────
    quality = _calculate_quality_score(scraped, analysis, bool(search_results))
    
    # Generate Confidence Indicators for graceful degradation
    if quality >= 0.8:
        confidence_level = "High"
        confidence_reason = "Comprehensive public data was retrieved successfully."
    elif quality >= 0.4:
        confidence_level = "Medium"
        confidence_reason = "Limited publicly accessible website content was available for deep technical assessment."
    else:
        confidence_level = "Low"
        confidence_reason = "The system gracefully degraded to business-level analysis due to missing data or blocked requests."

    logger.info(f"Enrichment quality score for {lead.company}: {quality:.2f} ({confidence_level} Confidence)")

    enriched = EnrichedCompanyData(
        lead=lead,
        scraped=scraped,
        analysis=analysis,
        enriched_at=datetime.utcnow(),
        data_quality_score=quality,
        confidence_level=confidence_level,
        confidence_reason=confidence_reason,
    )

    logger.info(f"Enrichment pipeline complete for {lead.company}")
    return enriched
