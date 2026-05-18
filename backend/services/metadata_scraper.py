import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, Any

class MetadataOnlyScraper:
    """
    A lightweight scraper that aims only to extract basic metadata 
    when full scraping tools (like Firecrawl or Playwright) fail.
    It extracts title, description, social links, and easily identifiable emails.
    """
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    async def scrape(self, url: str) -> Dict[str, Any]:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        try:
            # We use a standard User-Agent to avoid immediate generic blocks
            headers = {"User-Agent": "Mozilla/5.0 (compatible; LeadAutopilotMetadataBot/1.0)"}
            async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                html = response.text
        except Exception as e:
            # If even the basic fetch fails, return minimal structured data with the error
            return {
                "url": url,
                "domain": domain,
                "title": "",
                "description": "",
                "social_links": [],
                "contact_emails": [],
                "error": f"Metadata fetch failed: {str(e)}"
            }

        soup = BeautifulSoup(html, 'html.parser')

        # 1. Extract Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            og_title = soup.find("meta", property="og:title")
            if og_title and isinstance(og_title, dict) and "content" in og_title:
               title = str(og_title.get("content", "")).strip()

        # 2. Extract Description
        description = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if desc_tag:
            description = desc_tag.get("content", "").strip()

        # 3. Extract Social Links
        social_domains = ['linkedin.com', 'twitter.com', 'x.com', 'facebook.com', 'github.com', 'instagram.com', 'youtube.com']
        social_links = set()
        for a_tag in soup.find_all('a', href=True):
            href = str(a_tag['href'])
            for s_domain in social_domains:
                if s_domain in href:
                    social_links.add(href)
                    break

        # 4. Extract Emails via mailto: and regex
        contact_emails = set()
        
        # via mailto
        for a_tag in soup.find_all('a', href=True):
            href = str(a_tag['href'])
            if href.lower().startswith('mailto:'):
                email = href[7:].split('?')[0].strip()
                if email:
                    contact_emails.add(email)

        # via simple regex in text body
        # Basic check to avoid grabbing non-emails, specifically ignoring image extensions etc.
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        text_content = soup.get_text()
        text_emails = re.findall(email_pattern, text_content)
        for email in text_emails:
            # Filter out common false positives like file.png@2x
            if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                contact_emails.add(email)

        return {
            "url": url,
            "domain": domain,
            "title": title,
            "description": description,
            "social_links": list(social_links),
            "contact_emails": list(contact_emails)
        }
