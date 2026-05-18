"""
Web Search Enrichment Module.

Uses Serper.dev API to search Google for recent news, reviews,
and public information about a company. This adds context that
website scraping alone can't capture.

Activated when SERPER_API_KEY is set in environment.
Gracefully returns empty results when not configured.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"
REQUEST_TIMEOUT = 10.0


async def search_company_info(company_name: str, industry: str = "") -> dict:
    """
    Search Google for company information via Serper.dev API.

    Returns a dict with:
        - news: list of recent news snippets
        - organic: list of top search result snippets
        - people_also_ask: related questions
        - knowledge_graph: structured company info if available

    Returns empty dict if Serper is not configured or search fails.
    """
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        logger.info("SERPER_API_KEY not set — skipping web search enrichment")
        return {}

    try:
        query = f"{company_name} company"
        if industry and industry != "General":
            query += f" {industry}"

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            # Main search
            response = await client.post(
                SERPER_URL,
                json={"q": query, "num": 8},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code != 200:
                logger.warning(f"Serper search failed: HTTP {response.status_code}")
                return {}

            data = response.json()

            # Also search for news
            news_response = await client.post(
                "https://google.serper.dev/news",
                json={"q": f"{company_name} company news", "num": 5},
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            news_data = {}
            if news_response.status_code == 200:
                news_data = news_response.json()

        # Extract relevant data
        result = {
            "organic_results": [],
            "news": [],
            "people_also_ask": [],
            "knowledge_graph": {},
        }

        # Organic search results
        for item in data.get("organic", [])[:6]:
            result["organic_results"].append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
            })

        # News
        for item in news_data.get("news", [])[:5]:
            result["news"].append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", ""),
                "source": item.get("source", ""),
            })

        # People Also Ask
        for item in data.get("peopleAlsoAsk", [])[:4]:
            result["people_also_ask"].append({
                "question": item.get("question", ""),
                "answer": item.get("snippet", ""),
            })

        # Knowledge Graph
        kg = data.get("knowledgeGraph", {})
        if kg:
            result["knowledge_graph"] = {
                "title": kg.get("title", ""),
                "type": kg.get("type", ""),
                "description": kg.get("description", ""),
                "website": kg.get("website", ""),
                "founded": kg.get("attributes", {}).get("Founded", ""),
                "headquarters": kg.get("attributes", {}).get("Headquarters", ""),
                "ceo": kg.get("attributes", {}).get("CEO", ""),
                "employees": kg.get("attributes", {}).get("Number of employees", ""),
                "revenue": kg.get("attributes", {}).get("Revenue", ""),
            }

        total = len(result["organic_results"]) + len(result["news"])
        logger.info(f"Web search complete for {company_name}: {total} results found")
        return result

    except Exception as e:
        logger.warning(f"Web search failed for {company_name}: {e}")
        return {}


def format_search_context(search_results: dict) -> str:
    """
    Format search results into a text context string for the AI prompt.
    """
    if not search_results:
        return ""

    parts = []

    # Knowledge Graph
    kg = search_results.get("knowledge_graph", {})
    if kg and kg.get("description"):
        parts.append(f"GOOGLE KNOWLEDGE PANEL:\n{kg.get('description', '')}")
        details = []
        if kg.get("founded"):
            details.append(f"Founded: {kg['founded']}")
        if kg.get("headquarters"):
            details.append(f"HQ: {kg['headquarters']}")
        if kg.get("ceo"):
            details.append(f"CEO: {kg['ceo']}")
        if kg.get("employees"):
            details.append(f"Employees: {kg['employees']}")
        if kg.get("revenue"):
            details.append(f"Revenue: {kg['revenue']}")
        if details:
            parts.append(" | ".join(details))

    # Top search results
    organic = search_results.get("organic_results", [])
    if organic:
        snippets = [f"- {r['title']}: {r['snippet']}" for r in organic[:4] if r.get("snippet")]
        if snippets:
            parts.append("TOP SEARCH RESULTS:\n" + "\n".join(snippets))

    # Recent news
    news = search_results.get("news", [])
    if news:
        news_items = []
        for n in news[:3]:
            item = f"- [{n.get('date', '')}] {n['title']}"
            if n.get("snippet"):
                item += f": {n['snippet']}"
            news_items.append(item)
        if news_items:
            parts.append("RECENT NEWS:\n" + "\n".join(news_items))

    return "\n\n".join(parts)
