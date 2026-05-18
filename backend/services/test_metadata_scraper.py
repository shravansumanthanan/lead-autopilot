import pytest
import httpx
from unittest.mock import patch, MagicMock

from backend.services.metadata_scraper import MetadataOnlyScraper

@pytest.mark.asyncio
async def test_metadata_scraper_success():
    scraper = MetadataOnlyScraper()
    
    # Minimal mock HTML containing title, description, social links, and emails
    mock_html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>
                Test Company | Enterprise Resilience
            </title>
            <meta name="description" content="We break things so you don't have to.">
        </head>
        <body>
            <footer>
                <a href="https://linkedin.com/company/test-company">Follow us on LinkedIn</a>
                <a href="https://x.com/testcompany">X</a>
                
                <p>Contact sales at <a href="mailto:sales@testcompany.com">sales@testcompany.com</a></p>
                <p>For support, please email support-team@testcompany.com directly.</p>
                <img src="logo.png@2x">
            </footer>
        </body>
    </html>
    """
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = MagicMock()
        mock_response.text = mock_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = await scraper.scrape("example.com")
        
        # Check basic domain parsing
        assert result["url"] == "https://example.com"
        assert result["domain"] == "example.com"
        
        # Check meta extraction
        assert result["title"] == "Test Company | Enterprise Resilience"
        assert result["description"] == "We break things so you don't have to."
        
        # Check social extraction
        assert len(result["social_links"]) == 2
        assert "https://linkedin.com/company/test-company" in result["social_links"]
        assert "https://x.com/testcompany" in result["social_links"]
        
        # Check email extraction (both mailto: and regex)
        assert len(result["contact_emails"]) == 2
        assert "sales@testcompany.com" in result["contact_emails"]
        assert "support-team@testcompany.com" in result["contact_emails"]
        
        assert "error" not in result

@pytest.mark.asyncio
async def test_metadata_scraper_http_failure():
    scraper = MetadataOnlyScraper()
    
    with patch('httpx.AsyncClient.get', side_effect=httpx.ConnectTimeout("Timeout")):
        result = await scraper.scrape("https://example.com")
        
        # Should degrade gracefully
        assert result["title"] == ""
        assert result["description"] == ""
        assert len(result["social_links"]) == 0
        assert len(result["contact_emails"]) == 0
        
        # Error should be recorded
        assert "error" in result
        assert "Timeout" in result["error"]
