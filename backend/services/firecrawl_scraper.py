"""
Firecrawl Enrichment Module (Optional).

Uses Firecrawl API to scrape company websites with full JS rendering,
producing cleaner structured data than raw HTTPX+BS4 for modern
single-page applications.

Activated when FIRECRAWL_API_KEY is set in environment.
Falls back to basic scraper when not configured.
"""

from __future__ import annotations

import logging
import os

from core_models import ScrapedData

logger = logging.getLogger(__name__)


async def scrape_with_firecrawl(website_url: str) -> ScrapedData | None:
    """
    Scrape a website using Firecrawl API.

    Returns ScrapedData if successful, None if Firecrawl is not configured
    or the scrape fails (caller should fall back to basic scraper).
    """
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        logger.info("FIRECRAWL_API_KEY not set — skipping Firecrawl enrichment")
        return None

    try:
        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=api_key)

        logger.info(f"Firecrawl: scraping {website_url}")

        # Scrape the main page
        result = app.scrape_url(
            website_url,
            params={
                "formats": ["markdown", "extract"],
                "extract": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "company_name": {"type": "string"},
                            "tagline": {"type": "string"},
                            "description": {"type": "string"},
                            "services": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "about": {"type": "string"},
                            "contact_email": {"type": "string"},
                            "contact_phone": {"type": "string"},
                            "social_links": {
                                "type": "object",
                                "properties": {
                                    "linkedin": {"type": "string"},
                                    "x": {"type": "string"},
                                    "github": {"type": "string"},
                                    "facebook": {"type": "string"},
                                },
                            },
                        },
                    },
                    "prompt": "Extract the company information, services/products offered, about/mission text, contact details, and social media links from this page.",
                },
            },
        )

        if not result:
            logger.warning("Firecrawl returned empty result")
            return None

        # Map Firecrawl result to our ScrapedData model
        extract = result.get("extract", {}) or {}
        metadata = result.get("metadata", {}) or {}
        markdown = result.get("markdown", "") or ""

        social = extract.get("social_links", {}) or {}
        contact = {}
        if extract.get("contact_email"):
            contact["email"] = extract["contact_email"]
        if extract.get("contact_phone"):
            contact["phone"] = extract["contact_phone"]

        data = ScrapedData(
            title=metadata.get("title", "") or extract.get("company_name", ""),
            meta_description=metadata.get("description", "") or extract.get("tagline", ""),
            hero_text=extract.get("tagline", "") or extract.get("description", "")[:300],
            about_text=extract.get("about", "") or extract.get("description", ""),
            services=extract.get("services", []) or [],
            social_links={k: v for k, v in social.items() if v},
            contact_info=contact,
            raw_text_snippet=markdown[:3000] if markdown else "",
        )

        logger.info(
            f"Firecrawl scrape complete: title={bool(data.title)}, "
            f"services={len(data.services)}, about={bool(data.about_text)}"
        )
        return data

    except ImportError:
        logger.warning("firecrawl-py not installed — skipping")
        return None
    except Exception as e:
        logger.warning(f"Firecrawl scrape failed: {e}")
        return None
