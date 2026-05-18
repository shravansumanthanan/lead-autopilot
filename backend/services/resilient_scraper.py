import logging
from typing import List, Dict, Any, Tuple

from core_models import ScrapedData
from services.firecrawl_scraper import scrape_with_firecrawl
from services.scraper import scrape_company_website
from services.metadata_scraper import MetadataOnlyScraper
from utils.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from utils.retry import with_retry
from utils.timeout import with_timeout

logger = logging.getLogger(__name__)

class ResilientScraperService:
    """
    A service that wraps scraping functionality with fallbacks, circuit breakers,
    retries, and timeouts to ensure maximum resilience when fetching website data.
    """
    def __init__(self):
        # Firecrawl circuit breaker is more sensitive because it's a paid/external API
        self.firecrawl_cb = get_circuit_breaker("firecrawl", failure_threshold=3, recovery_timeout=60.0)
        # Basic scraper circuit breaker
        self.basic_cb = get_circuit_breaker("basic_scraper", failure_threshold=5, recovery_timeout=30.0)
        # Metadata scraper is the final fallback, very lightweight
        self.metadata_scraper = MetadataOnlyScraper(timeout=10)

    @with_timeout(timeout=30.0)
    async def scrape_with_fallbacks(self, url: str) -> Tuple[ScrapedData, List[str]]:
        """
        Attempt to scrape a URL using a descending hierarchy of scraper implementations.
        Returns the resulting ScrapedData and a list of warnings encountered.
        Fallback Hierarchy: Firecrawl -> Basic -> Playwright (skipped) -> Metadata
        """
        warnings = []
        
        # 1. Try Firecrawl
        try:
            logger.info("Attempting scrape with Firecrawl")
            data = await self._run_firecrawl(url)
            if data:
                return data, warnings
            else:
                warnings.append("Firecrawl returned None, falling back to basic scraper.")
        except CircuitBreakerOpenError:
            warnings.append("Firecrawl circuit breaker open, skipping.")
        except Exception as e:
            warnings.append(f"Firecrawl failed: {str(e)}")

        # 2. Try Basic
        try:
            logger.info("Attempting scrape with Basic Scraper")
            data = await self._run_basic(url)
            if data:
                return data, warnings
        except CircuitBreakerOpenError:
            warnings.append("Basic scraper circuit breaker open, skipping.")
        except Exception as e:
            warnings.append(f"Basic scraper failed: {str(e)}")

        # 3. Try Playwright
        warnings.append("Playwright scraper not implemented, skipping to Metadata.")

        # 4. Try Metadata
        try:
            logger.info("Attempting scrape with Metadata Scraper")
            raw_meta = await self._run_metadata(url)
            if raw_meta:
                # Convert Dict to ScrapedData
                data = ScrapedData(
                    title=raw_meta.get("title", ""),
                    meta_description=raw_meta.get("description", ""),
                    social_links={link: link for link in raw_meta.get("social_links", [])},
                    contact_info={"emails": ", ".join(raw_meta.get("contact_emails", []))}
                )
                if "error" in raw_meta:
                    warnings.append(f"Metadata scraper had partial error: {raw_meta['error']}")
                return data, warnings
        except Exception as e:
            warnings.append(f"Metadata scraper failed: {str(e)}")

        # Absolute Failure
        warnings.append("All scraping methods failed to extract data.")
        return ScrapedData(), warnings

    @with_retry(retries=3, base_delay=1.0)
    async def _run_firecrawl(self, url: str) -> ScrapedData | None:
        """Isolated wrapper to cleanly track retries and circuit breaking."""
        return await self.firecrawl_cb.call_with_breaker(scrape_with_firecrawl, url)

    @with_retry(retries=2, base_delay=1.0)
    async def _run_basic(self, url: str) -> ScrapedData:
        """Isolated wrapper for the basic scraping engine."""
        return await self.basic_cb.call_with_breaker(scrape_company_website, url)

    @with_retry(retries=2, base_delay=1.0)
    async def _run_metadata(self, url: str) -> Dict[str, Any]:
        """Isolated wrapper for the metadata fallback engine."""
        return await self.metadata_scraper.scrape(url)
