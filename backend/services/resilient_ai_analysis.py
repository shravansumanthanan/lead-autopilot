import logging
import json
from typing import Tuple, List

from openai import AsyncOpenAI, RateLimitError
from pydantic import ValidationError

from core_models import AIAnalysis, ScrapedData
from services.ai_analysis import _build_analysis_prompt, _get_client, _get_model, _parse_ai_response
from services.fallback_generator import FallbackContentGenerator
from services.content_validator import ContentValidator
from utils.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
from utils.retry import with_retry
from utils.timeout import with_timeout

logger = logging.getLogger(__name__)

class AIAnalysisError(Exception):
    """Custom exception for AI analysis failures (JSON decoding, schema validation, hallucination)."""
    pass

class ResilientAIAnalysisService:
    """
    Service for executing AI analysis with resilience patterns:
    - Circuit Breaking
    - Timeouts (45s)
    - Retries (JSON/Rate Limit issues)
    - Hallucination detection (ContentValidator)
    - Structured fallbacks (FallbackContentGenerator)
    """
    
    def __init__(self):
        self.circuit_breaker = get_circuit_breaker("ai_analysis", failure_threshold=3, recovery_timeout=120.0)
        self.fallback_generator = FallbackContentGenerator()
        self.content_validator = ContentValidator()

    @with_timeout(timeout=45.0)
    async def analyze_with_validation(
        self,
        company_name: str,
        industry: str,
        website_url: str,
        scraped: ScrapedData,
        prospect_message: str = "",
        web_search_context: str = ""
    ) -> Tuple[AIAnalysis, List[str]]:
        """
        Produce AI Analysis robustly. Returns the analysis object and a list of warnings.
        """
        warnings = []
        prompt = _build_analysis_prompt(company_name, industry, website_url, scraped, prospect_message, web_search_context)
        
        try:
            # We call the circuit breaker wrapped execution
            logger.info("Attempting AI Analysis through Resilient Wrapper.")
            
            # Bound retry parameters manually for the API operation
            analysis = await self._execute_and_validate(prompt, company_name)
            return analysis, warnings
            
        except CircuitBreakerOpenError:
            warnings.append("AI Service circuit breaker is OPEN. Fast-failing to fallback generation.")
        except RateLimitError as e:
            warnings.append(f"AI Service rate limited after retries. Falling back. Error: {e}")
        except Exception as e:
            warnings.append(f"AI Service failed: {e}. Utilizing structured industry fallbacks.")
            
        # Absolute Fallback execution if the AI completely fails
        logger.warning(f"Using Fallback Content Generator for {company_name}")
        fallback_analysis = self.fallback_generator.generate_fallback_analysis(company_name, industry, scraped)
        return fallback_analysis, warnings

    @with_retry(retries=2, base_delay=2.0)
    async def _execute_and_validate(self, prompt: str, company_name: str) -> AIAnalysis:
        """
        Execute the OpenRouter call directly to enable validation retries.
        Wrapped with Circuit Breaker calls internally.
        """
        return await self.circuit_breaker.call_with_breaker(
            self._do_api_call_and_parse, prompt, company_name
        )

    async def _do_api_call_and_parse(self, prompt: str, company_name: str) -> AIAnalysis:
        """The actual network execution and parsing block."""
        client = _get_client()
        model = _get_model()

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
            temperature=0.6,
            max_tokens=2500,
            extra_headers={
                "HTTP-Referer": "https://github.com/lead-autopilot",
                "X-Title": "Lead Autopilot",
            },
        )

        response_text = response.choices[0].message.content or ""
        
        # 1. Parse JSON
        parsed_dict = _parse_ai_response(response_text)
        if not parsed_dict:
            raise AIAnalysisError("AI Response could not be parsed to JSON.")
            
        # 2. Validate Schema (Pydantic validates fields inherently on init)
        try:
            analysis = AIAnalysis(**parsed_dict)
        except ValidationError as e:
            raise AIAnalysisError(f"AI Output failed schema validation: {e}")

        # 3. Detect Hallucinations / Loops
        target_texts = [analysis.executive_summary, analysis.current_state_assessment]
        for t_idx, text in enumerate(target_texts):
            if self.content_validator.detect_repetitive_content(text):
                raise AIAnalysisError(f"Repetitive content loop detected in field index {t_idx}.")

        return analysis
