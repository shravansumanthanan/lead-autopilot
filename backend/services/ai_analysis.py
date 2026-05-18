"""
AI Analyzer Module.

Uses OpenRouter API (Qwen model) via OpenAI-compatible SDK to generate
personalized company analysis including:
- Company overview
- Industry analysis
- SWOT analysis
- Digital presence assessment
- Personalized recommendations

All analysis is grounded in the scraped website data to ensure accuracy
and relevance.
"""

from __future__ import annotations

import json
import logging
import os
from textwrap import dedent

from openai import AsyncOpenAI

from core_models import AIAnalysis, ScrapedData, SWOTAnalysis, Scorecard, ActionItem
from utils.retry import with_retry
from utils.validation import validate_schema

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────


def _get_client() -> AsyncOpenAI:
    """Create an OpenRouter-compatible OpenAI client."""
    return AsyncOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    )


def _get_model() -> str:
    """Get the configured model name."""
    return os.getenv("OPENROUTER_MODEL", "qwen/qwen3-235b-a22b")


# ── Prompt Construction ──────────────────────────────────────────────────────

def _build_analysis_prompt(
    company_name: str,
    industry: str,
    website_url: str,
    scraped: ScrapedData,
    prospect_message: str = "",
    web_search_context: str = "",
) -> str:
    """Build a comprehensive analysis prompt from scraped + web search data."""

    scraped_context = f"""
SCRAPED WEBSITE DATA:
- Website Title: {scraped.title or 'N/A'}
- Meta Description: {scraped.meta_description or 'N/A'}
- Hero/Headline Text: {scraped.hero_text or 'N/A'}
- About Page Content: {scraped.about_text[:1500] if scraped.about_text else 'N/A'}
- Services/Products Found: {', '.join(scraped.services) if scraped.services else 'N/A'}
- Technology Stack Detected: {', '.join(scraped.tech_stack) if scraped.tech_stack else 'N/A'}
- Social Media Presence: {', '.join(f'{k}: {v}' for k, v in scraped.social_links.items()) if scraped.social_links else 'N/A'}
- Main Page Content Snippet: {scraped.raw_text_snippet[:1000] if scraped.raw_text_snippet else 'N/A'}
""".strip()

    prospect_context = ""
    if prospect_message:
        prospect_context = f"\nPROSPECT'S MESSAGE/PAIN POINTS:\n{prospect_message}\n"

    search_section = ""
    if web_search_context:
        search_section = f"\nWEB SEARCH INTELLIGENCE (from Google):\n{web_search_context}\n"

    prompt = dedent(f"""
    You are a senior Deloitte business consultant preparing a personalized company audit report for an executive audience.
    
    Analyze the following company and provide a comprehensive, insightful report.
    Your analysis must be grounded in the actual data provided.
    
    CRITICAL TONE GUIDELINES:
    1. Tone must be confident, neutral, analytical, and highly strategic.
    2. NEVER insult the company. Frame weaknesses as "optimization opportunities", "maturity gaps", or "strategic improvements".
    3. Use short paragraphs, precise wording, and business-first language (e.g., instead of "bad SEO", use "under-optimized discoverability elements").
    4. Focus on business impact, not engineering depth.
    
    COMPANY INFORMATION:
    - Company Name: {company_name}
    - Industry: {industry}
    - Website: {website_url}
    {prospect_context}
    {scraped_context}
    {search_section}
    
    Provide your analysis as a JSON object with EXACTLY this structure:
    {{
        "executive_summary": "A dense, strategic 1-2 paragraph summary of the business context and main observations.",
        "current_state_assessment": "Assessment of their digital maturity, positioning, and customer experience. 2 paragraphs.",
        "swot": {{
            "strengths": ["Strategic strength 1", "Strategic strength 2", "Strategic strength 3"],
            "weaknesses": ["Optimization area 1", "Optimization area 2", "Optimization area 3"],
            "opportunities": ["Growth potential 1", "Growth potential 2", "Growth potential 3"],
            "threats": ["Market risk 1", "Market risk 2", "Market risk 3"]
        }},
        "key_findings": [
            {{"category": "Digital Presence", "observation": "Professional insight..."}},
            {{"category": "Conversion Flow", "observation": "Professional insight..."}},
            {{"category": "Technical Foundation", "observation": "Professional insight..."}}
        ],
        "risk_areas": [
            "Specific operational or strategic risk 1",
            "Specific risk 2",
            "Specific risk 3"
        ],
        "strategic_opportunities": [
            "Impact-focused recommendation 1",
            "Impact-focused recommendation 2",
            "Impact-focused recommendation 3"
        ],
        "scorecard": {{
            "digital_maturity": 7,
            "ai_readiness": 5,
            "seo_foundation": 6
        }},
        "action_roadmap": [
            {{"timeline": "Immediate", "recommendation": "High-impact quick win", "impact": "High", "effort": "Low"}},
            {{"timeline": "30 Days", "recommendation": "Medium-term strategic initiative", "impact": "High", "effort": "Medium"}},
            {{"timeline": "90 Days", "recommendation": "Long-term maturity investment", "impact": "Medium", "effort": "High"}}
        ]
    }}
    
    Return ONLY the JSON object, no markdown fencing or additional text.
    """).strip()

    return prompt


# ── JSON Parsing ─────────────────────────────────────────────────────────────

def _parse_ai_response(response_text: str) -> dict:
    """Parse the AI response, handling common formatting issues."""
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        # Remove first line (```json or ```)
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()

    # Try to find JSON object in the response
    # Sometimes models add text before/after the JSON
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]

    try:
        parsed_data = json.loads(text)
        # Use our validation logic if necessary, but returning dict first is fine for now
        return parsed_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        logger.debug(f"Raw response: {response_text[:500]}")
        return {}


def _dict_to_analysis(data: dict) -> AIAnalysis:
    """Convert parsed JSON dict to AIAnalysis model."""
    swot_data = data.get("swot", {})
    swot = SWOTAnalysis(
        strengths=swot_data.get("strengths", []),
        weaknesses=swot_data.get("weaknesses", []),
        opportunities=swot_data.get("opportunities", []),
        threats=swot_data.get("threats", []),
    )
    
    scorecard_data = data.get("scorecard", {})
    scorecard = Scorecard(
        digital_maturity=scorecard_data.get("digital_maturity", 5),
        ai_readiness=scorecard_data.get("ai_readiness", 5),
        seo_foundation=scorecard_data.get("seo_foundation", 5)
    )
    
    roadmap = [ActionItem(**item) for item in data.get("action_roadmap", [])]

    return AIAnalysis(
        executive_summary=data.get("executive_summary", ""),
        current_state_assessment=data.get("current_state_assessment", ""),
        swot=swot,
        key_findings=data.get("key_findings", []),
        risk_areas=data.get("risk_areas", []),
        strategic_opportunities=data.get("strategic_opportunities", []),
        scorecard=scorecard,
        action_roadmap=roadmap
    )


# ── Public API ───────────────────────────────────────────────────────────────

@with_retry(retries=2, base_delay=2.0)
async def _execute_analysis_call(prompt: str, company_name: str) -> dict:
    client = _get_client()
    model = _get_model()

    logger.info(f"Sending analysis request to OpenRouter ({model}) for {company_name}")

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior business analyst. You provide accurate, insightful, "
                    "and well-structured company analysis reports. Always respond with valid JSON only. "
                    "Do not use markdown formatting or code fences. Do not think or reason out loud — "
                    "respond directly with the JSON object."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
    )

    response_text = response.choices[0].message.content or ""
    logger.info(f"Received AI response ({len(response_text)} chars)")

    parsed = _parse_ai_response(response_text)
    if not parsed:
        raise ValueError("Failed to parse AI JSON response")
    
    return parsed

async def analyze_company(
    company_name: str,
    industry: str,
    website_url: str,
    scraped: ScrapedData,
    prospect_message: str = "",
    web_search_context: str = "",
) -> AIAnalysis:
    """
    Generate AI-powered company analysis using OpenRouter (Qwen).

    Args:
        company_name: Name of the company.
        industry: Industry/sector.
        website_url: Company website URL.
        scraped: Data scraped from the company website.
        prospect_message: Optional message from the prospect.
        web_search_context: Formatted text from web search results.

    Returns:
        AIAnalysis with all generated insights.

    This function never raises — returns empty analysis on failure.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not set — skipping AI analysis")
        return AIAnalysis(
            executive_summary=f"{company_name} operates in the {industry} sector. "
            "Our automated research indicates potential for optimization. A full "
            "AI assessment could not be completed for this profile due to connection limitations.",
            action_roadmap=[
                ActionItem(timeline="Immediate", recommendation="Review automated digital presence scores"),
                ActionItem(timeline="Short Term", recommendation="Ensure tech stack is fully utilized")
            ]
        )

    prompt = _build_analysis_prompt(company_name, industry, website_url, scraped, prospect_message, web_search_context)

    try:
        parsed_dict = await _execute_analysis_call(prompt, company_name)
        
        # Use our schema validation
        analysis = validate_schema(parsed_dict, AIAnalysis)
        if not analysis:
            logger.warning("AI response failed schema validation — falling back to dict conversion")
            analysis = _dict_to_analysis(parsed_dict)
            
        logger.info(f"AI analysis complete for {company_name}")
        return analysis

    except Exception as e:
        logger.error(f"AI analysis failed for {company_name}: {e}")
        return AIAnalysis(
            executive_summary=f"{company_name} is a company in the {industry} space. "
            "A detailed AI breakdown could not be generated at this time.",
            action_roadmap=[ActionItem(timeline="Immediate", recommendation="Verify website URL and try again later.")]
        )
