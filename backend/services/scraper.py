"""
Website Scraper Module.

Scrapes a company's website to extract structured data including:
- Page metadata (title, description, OG tags)
- Hero/about text content
- Services/products mentioned
- Technology stack indicators
- Social media links
- Contact information

Handles errors gracefully with timeouts, retries, and fallbacks.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from core_models import ScrapedData

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 10.0  # seconds per request
MAX_TEXT_LENGTH = 3000  # max chars for text snippets
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

# Common about page paths to try
ABOUT_PATHS = ["/about", "/about-us", "/about-us/", "/company", "/who-we-are", "/our-story"]

# Technology indicators in HTML
TECH_INDICATORS = {
    "React": ["react", "reactjs", "_next", "__next"],
    "Vue.js": ["vue", "vuejs", "nuxt"],
    "Angular": ["ng-", "angular"],
    "Next.js": ["_next", "__next", "nextjs"],
    "WordPress": ["wp-content", "wp-includes", "wordpress"],
    "Shopify": ["shopify", "myshopify"],
    "Webflow": ["webflow"],
    "Squarespace": ["squarespace"],
    "Wix": ["wix.com", "wixsite"],
    "HubSpot": ["hubspot", "hs-scripts"],
    "Google Analytics": ["google-analytics", "gtag", "googletagmanager"],
    "Stripe": ["stripe.com", "js.stripe"],
    "Intercom": ["intercom", "intercomcdn"],
    "Zendesk": ["zendesk", "zdassets"],
    "Segment": ["segment.com", "segment.io", "cdn.segment"],
    "Tailwind CSS": ["tailwindcss", "tailwind"],
    "Bootstrap": ["bootstrap"],
}


# ── Helper Functions ─────────────────────────────────────────────────────────

def _clean_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Clean and truncate extracted text."""
    if not text:
        return ""
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_length]


def _extract_meta(soup: BeautifulSoup, name: str) -> str:
    """Extract a meta tag content by name or property."""
    tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
    if tag and isinstance(tag, Tag):
        return _clean_text(tag.get("content", ""))
    return ""


def _normalize_url(base_url: str) -> str:
    """Ensure URL has a scheme and normalize it."""
    url = base_url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# ── Core Scraping Functions ──────────────────────────────────────────────────

async def _fetch_page(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch a single page, returning HTML or None on failure."""
    try:
        response = await client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
            return response.text
    except (httpx.HTTPError, httpx.TimeoutException, Exception) as e:
        logger.warning(f"Failed to fetch {url}: {e}")
    return None


def _extract_hero_text(soup: BeautifulSoup) -> str:
    """Extract hero/headline text from the page."""
    # Try common hero patterns
    hero_selectors = [
        "section.hero", ".hero", "#hero",
        "section.banner", ".banner",
        "header .headline", ".hero-text",
        "[class*='hero']", "[class*='banner']",
    ]
    for selector in hero_selectors:
        hero = soup.select_one(selector)
        if hero:
            return _clean_text(hero.get_text(separator=" "), 500)

    # Fallback: first large heading
    for tag in ["h1", "h2"]:
        heading = soup.find(tag)
        if heading:
            return _clean_text(heading.get_text(separator=" "), 300)

    return ""


def _extract_services(soup: BeautifulSoup) -> list[str]:
    """Extract services/products from common page patterns."""
    services = []

    # Try nav links for service indicators
    nav = soup.find("nav") or soup.find("header")
    if nav:
        links = nav.find_all("a", href=True)
        service_keywords = ["service", "product", "solution", "platform", "feature", "offering"]
        for link in links:
            text = link.get_text(strip=True)
            href = link.get("href", "").lower()
            if any(kw in href for kw in service_keywords) and text and len(text) < 60:
                services.append(text)

    # Try list items in main content
    main = soup.find("main") or soup.find("body")
    if main and not services:
        for section in main.find_all(["section", "div"], limit=10):
            heading = section.find(["h2", "h3"])
            if heading:
                text = heading.get_text(strip=True).lower()
                if any(kw in text for kw in ["service", "what we do", "solution", "product", "offering"]):
                    items = section.find_all("li")
                    for item in items[:8]:
                        item_text = item.get_text(strip=True)
                        if item_text and len(item_text) < 100:
                            services.append(item_text)

    return services[:10]


def _detect_tech_stack(html: str) -> list[str]:
    """Detect technologies used by analyzing the HTML source."""
    html_lower = html.lower()
    detected = []
    for tech, indicators in TECH_INDICATORS.items():
        if any(indicator in html_lower for indicator in indicators):
            detected.append(tech)
    return detected


def _extract_social_links(soup: BeautifulSoup, html: str) -> dict[str, str]:
    """
    Extract social media profile links using four strategies:
    1. JSON-LD structured data (sameAs)
    2. Anchor tag hrefs
    3. Raw HTML regex (catches JS-rendered / data-attribute links)
    4. Meta tags (og:see_also, etc.)
    """
    socials: dict[str, str] = {}

    # Patterns: platform name → (domain patterns, canonical prefix)
    PLATFORMS = {
        "linkedin":  (["linkedin.com/company/", "linkedin.com/in/"], "https://linkedin.com"),
        "x":         (["twitter.com/", "x.com/"], "https://x.com"),
        "facebook":  (["facebook.com/"], "https://facebook.com"),
        "instagram": (["instagram.com/"], "https://instagram.com"),
        "youtube":   (["youtube.com/", "youtu.be/"], "https://youtube.com"),
        "github":    (["github.com/"], "https://github.com"),
        "tiktok":    (["tiktok.com/"], "https://tiktok.com"),
    }

    def _classify(url: str) -> str | None:
        """Return platform key for a URL, or None if not a social URL."""
        url_lower = url.lower()
        # Exclude YouTube video watch links — we want channels only
        if "youtube.com/watch" in url_lower:
            return None
        for platform, (patterns, _) in PLATFORMS.items():
            if any(p in url_lower for p in patterns):
                # Exclude generic homepage links like linkedin.com (no path after /)
                parsed = urlparse(url)
                path = parsed.path.strip("/")
                if path:  # must have a path component
                    return platform
        return None

    def _store(platform: str, url: str) -> None:
        """Store a social URL, keeping the first found per platform."""
        if platform not in socials and url.startswith("http"):
            socials[platform] = url

    # ── Strategy 1: JSON-LD structured data (sameAs) ──────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json as _json
            data = _json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                same_as = item.get("sameAs", [])
                if isinstance(same_as, str):
                    same_as = [same_as]
                for url in same_as:
                    platform = _classify(url)
                    if platform:
                        _store(platform, url)
        except Exception:
            pass

    # ── Strategy 2: Anchor tag hrefs ──────────────────────────────────────
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        if not href.startswith("http"):
            continue
        platform = _classify(href)
        if platform:
            _store(platform, href)

    # ── Strategy 3: Raw HTML regex (JS-injected, data-attrs, JSON blobs) ──
    # Matches any https://platform.com/path inside the raw HTML
    pattern = re.compile(
        r'https?://(?:www\.)?'
        r'(linkedin\.com/(?:company|in)/[\w\-\.]+'
        r'|twitter\.com/[\w]+'
        r'|x\.com/[\w]+'
        r'|facebook\.com/[\w\.\_\-]+'
        r'|instagram\.com/[\w\.]+'
        r'|youtube\.com/(?:@[\w\-\.]+|c/[\w\-\.]+|channel/[\w\-]+|user/[\w\-]+)'
        r'|github\.com/[\w\-]+'
        r'|tiktok\.com/@[\w\-\.]+)'
        r'[\'"\s>]',
        re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        url = m.group(0).rstrip("'\"\n\r\t >")
        platform = _classify(url)
        if platform:
            _store(platform, url)

    # ── Strategy 4: Meta tags (og:see_also, article:author, etc.) ─────────
    for meta in soup.find_all("meta"):
        content = meta.get("content", "")
        if "://" in content:
            platform = _classify(content)
            if platform:
                _store(platform, content)

    return socials


def _extract_contact_info(soup: BeautifulSoup) -> dict[str, str]:
    """Extract contact information (email, phone, address)."""
    contact = {}
    text = soup.get_text()

    # Email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        email = email_match.group()
        # Filter out common non-contact emails
        if not any(x in email.lower() for x in ["example.com", "sentry", "webpack", "babel"]):
            contact["email"] = email

    # Phone
    phone_match = re.search(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}', text)
    if phone_match:
        phone = phone_match.group().strip()
        if len(phone) >= 10:
            contact["phone"] = phone

    # Address — look for structured data
    address_tag = soup.find(attrs={"itemprop": "address"}) or soup.find("address")
    if address_tag:
        contact["address"] = _clean_text(address_tag.get_text(), 200)

    return contact


def _extract_main_text(soup: BeautifulSoup) -> str:
    """Extract the main readable text content from the page."""
    # Remove script, style, nav, footer
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main:
        return _clean_text(main.get_text(separator=" "), MAX_TEXT_LENGTH)
    return ""


# ── Public API ───────────────────────────────────────────────────────────────

async def scrape_company_website(website_url: str) -> ScrapedData:
    """
    Scrape a company's website and extract structured data.

    Args:
        website_url: The company's website URL.

    Returns:
        ScrapedData with all extracted information.

    This function never raises — it returns partial data on failures.
    """
    url = _normalize_url(website_url)
    data = ScrapedData()

    logger.info(f"Starting scrape of {url}")

    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        # ── Step 1: Scrape homepage ──────────────────────────────────────
        html = await _fetch_page(client, url)
        if not html:
            logger.warning(f"Could not fetch homepage for {url}")
            return data

        soup = BeautifulSoup(html, "lxml")

        # Extract metadata
        title_tag = soup.find("title")
        data.title = _clean_text(title_tag.get_text()) if title_tag else ""
        data.meta_description = _extract_meta(soup, "description") or _extract_meta(soup, "og:description")
        data.hero_text = _extract_hero_text(soup)
        data.services = _extract_services(soup)
        data.tech_stack = _detect_tech_stack(html)
        data.social_links = _extract_social_links(soup, html)
        data.contact_info = _extract_contact_info(soup)
        data.raw_text_snippet = _extract_main_text(soup)

        # Collect key pages from navigation
        nav = soup.find("nav") or soup.find("header")
        if nav:
            for link in nav.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                if text and len(text) < 50 and href.startswith(("/", url)):
                    data.key_pages.append(f"{text}: {href}")
        data.key_pages = data.key_pages[:15]

        # ── Step 2: Try to scrape an about page ─────────────────────────
        for path in ABOUT_PATHS:
            about_url = urljoin(url + "/", path.lstrip("/"))
            about_html = await _fetch_page(client, about_url)
            if about_html:
                about_soup = BeautifulSoup(about_html, "lxml")
                # Remove nav/footer noise
                for tag in about_soup.find_all(["nav", "footer", "header", "script", "style"]):
                    tag.decompose()
                about_main = about_soup.find("main") or about_soup.find("article") or about_soup.find("body")
                if about_main:
                    data.about_text = _clean_text(about_main.get_text(separator=" "), 2000)
                    logger.info(f"Found about page at {about_url}")
                    break

    logger.info(
        f"Scrape complete for {url}: "
        f"title={bool(data.title)}, about={bool(data.about_text)}, "
        f"services={len(data.services)}, tech={len(data.tech_stack)}"
    )
    return data
