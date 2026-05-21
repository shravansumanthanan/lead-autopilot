"""
Smoke Tests for Lead Autopilot.

Validates that all modules import correctly, Pydantic models instantiate
without error, and core utilities behave as expected. These tests run
without external services (no Redis, OpenRouter, or SMTP required).

Run:
    cd backend && python -m pytest test_smoke.py -v
"""

import asyncio
import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

import pytest


# ── 1. Module Import Tests ──────────────────────────────────────────────────

class TestModuleImports:
    """Verify every module can be imported without crashing."""

    def test_import_core_models(self):
        from core_models import (
            LeadSubmission,
            ScrapedData,
            AIAnalysis,
            EnrichedCompanyData,
            PipelineStep,
            ErrorCategory,
            ErrorEvent,
            QualityScoreComponents,
        )

    def test_import_services(self):
        from services.scraper import scrape_company_website
        from services.resilient_scraper import ResilientScraperService
        from services.metadata_scraper import MetadataOnlyScraper
        from services.ai_analysis import _build_analysis_prompt
        from services.resilient_ai_analysis import ResilientAIAnalysisService
        from services.fallback_generator import FallbackContentGenerator
        from services.pdf_generator import generate_report_pdf
        from services.quality_scorer import QualityScoreCalculator
        from services.confidence_assigner import ConfidenceLevelAssigner, ConfidenceMetadata
        from services.content_validator import ContentValidator
        from services.error_categorizer import ErrorCategorizerService
        from services.web_search import search_company_info

    def test_import_utils(self):
        from utils.circuit_breaker import CircuitBreakerManager
        from utils.retry import RetryEngine, with_retry, NonRetryableError
        from utils.timeout import TimeoutManager, with_timeout
        from utils.validation import is_valid_url, normalize_url, validate_schema

    def test_import_workflows(self):
        from workflows.report_pipeline import run_enrichment_pipeline

    def test_import_integrations(self):
        from integrations.sheets import log_lead_to_sheets
        from integrations.drive import upload_pdf_to_drive
        from integrations.webhooks import send_slack_notification, send_crm_webhook


# ── 2. Pydantic Model Tests ────────────────────────────────────────────────

class TestPydanticModels:
    """Ensure core Pydantic models instantiate and validate correctly."""

    def test_lead_submission_valid(self):
        from core_models import LeadSubmission
        lead = LeadSubmission(
            name="Jane Smith",
            email="jane@acme.com",
            company="Acme Corp",
            website="https://acme.com",
            industry="SaaS",
        )
        assert lead.name == "Jane Smith"
        assert lead.email == "jane@acme.com"

    def test_lead_submission_rejects_url_without_scheme(self):
        from core_models import LeadSubmission
        with pytest.raises(Exception):
            LeadSubmission(
                name="Test",
                email="t@t.com",
                company="Test Co",
                website="acme.com",  # No scheme — Pydantic HttpUrl rejects this
                industry="General",
            )

    def test_lead_submission_rejects_bad_email(self):
        from core_models import LeadSubmission
        with pytest.raises(Exception):
            LeadSubmission(
                name="Test",
                email="not-an-email",
                company="Test Co",
                website="https://acme.com",
                industry="General",
            )

    def test_scraped_data_defaults(self):
        from core_models import ScrapedData
        data = ScrapedData()
        assert data.title == ""
        assert data.services == []
        assert data.tech_stack == []

    def test_ai_analysis_defaults(self):
        from core_models import AIAnalysis
        analysis = AIAnalysis()
        assert analysis.executive_summary == ""
        assert analysis.action_roadmap == []

    def test_enriched_company_data(self):
        from core_models import EnrichedCompanyData, LeadSubmission
        lead = LeadSubmission(
            name="Test", email="t@t.com", company="Test Co",
            website="https://test.com", industry="General",
        )
        enriched = EnrichedCompanyData(lead=lead)
        assert enriched.data_quality_score == 0.0
        assert enriched.confidence_level == "Low"

    def test_pipeline_step_enum(self):
        from core_models import PipelineStep
        assert PipelineStep.SUBMITTED.value == "submitted"
        assert PipelineStep.COMPLETE.value == "complete"
        assert PipelineStep.ERROR.value == "error"


# ── 3. Utility Tests ───────────────────────────────────────────────────────

class TestValidation:
    """Test URL validation and normalisation utilities."""

    def test_valid_urls(self):
        from utils.validation import is_valid_url
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("http://example.com") is True
        assert is_valid_url("example.com") is True

    def test_invalid_urls(self):
        from utils.validation import is_valid_url
        assert is_valid_url("") is False
        assert is_valid_url(None) is False
        assert is_valid_url("notadomain") is False

    def test_normalize_url(self):
        from utils.validation import normalize_url
        assert normalize_url("example.com") == "https://example.com"
        assert normalize_url("https://example.com/") == "https://example.com"


class TestContentValidator:
    """Test AI hallucination detection."""

    def test_clean_content(self):
        from services.content_validator import ContentValidator
        cv = ContentValidator()
        assert cv.detect_repetitive_content("This is a normal paragraph.") is False

    def test_repetitive_sentences(self):
        from services.content_validator import ContentValidator
        cv = ContentValidator()
        repeated = "This is repeated. " * 5
        assert cv.detect_repetitive_content(repeated) is True


class TestQualityScorer:
    """Test composite quality scoring."""

    def test_empty_data_gives_zero(self):
        from services.quality_scorer import QualityScoreCalculator
        calc = QualityScoreCalculator()
        result = calc.calculate_score()
        assert result.composite_score == 0.0

    def test_full_scraped_data_gives_positive_score(self):
        from services.quality_scorer import QualityScoreCalculator
        calc = QualityScoreCalculator()
        result = calc.calculate_score(scraped_data={
            "title": "Acme Corp",
            "meta_description": "We build things",
            "hero_text": "Welcome to Acme",
            "about_text": "We are a company...",
            "services": ["Consulting"],
            "contact_info": {"email": "hi@acme.com"},
        })
        assert result.composite_score > 0.0
        assert result.scraped_data_score > 0.0


class TestConfidenceAssigner:
    """Test confidence level assignment."""

    def test_high_confidence(self):
        from services.confidence_assigner import ConfidenceLevelAssigner, ConfidenceLevel
        from core_models import QualityScoreComponents
        assigner = ConfidenceLevelAssigner()
        scores = QualityScoreComponents(
            scraped_data_score=0.8,
            ai_analysis_score=0.9,
            web_search_score=0.7,
            composite_score=0.85,
        )
        result = assigner.assign_confidence(scores)
        assert result.level == ConfidenceLevel.HIGH

    def test_low_confidence(self):
        from services.confidence_assigner import ConfidenceLevelAssigner, ConfidenceLevel
        from core_models import QualityScoreComponents
        assigner = ConfidenceLevelAssigner()
        scores = QualityScoreComponents(
            scraped_data_score=0.0,
            ai_analysis_score=0.0,
            web_search_score=0.0,
            composite_score=0.0,
        )
        result = assigner.assign_confidence(scores)
        assert result.level == ConfidenceLevel.LOW
        assert "scraped_data" in result.missing_sources


class TestErrorCategorizer:
    """Test error categorization and user messages."""

    def test_scraping_blocked(self):
        from services.error_categorizer import ErrorCategorizerService
        from core_models import ErrorCategory
        svc = ErrorCategorizerService()
        event = svc.categorize_and_log(
            error=Exception("HTTP 403 Forbidden"),
            lead_id="test-123",
            component="scraper",
        )
        assert event.category == ErrorCategory.SCRAPING_BLOCKED
        assert event.recoverable is True
        assert event.user_facing_message  # should not be empty

    def test_unknown_error(self):
        from services.error_categorizer import ErrorCategorizerService
        from core_models import ErrorCategory
        svc = ErrorCategorizerService()
        event = svc.categorize_and_log(
            error=Exception("Something weird happened"),
            lead_id="test-456",
            component="unknown_component",
        )
        assert event.category == ErrorCategory.UNKNOWN


class TestRetryEngine:
    """Test retry logic without network calls."""

    @pytest.mark.asyncio
    async def test_succeeds_without_retry(self):
        from utils.retry import RetryEngine
        engine = RetryEngine(retries=3)
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await engine.execute(succeed)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        from utils.retry import RetryEngine
        engine = RetryEngine(retries=2, base_delay=0.01)
        call_count = 0

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        result = await engine.execute(fail_twice)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        from utils.retry import RetryEngine, NonRetryableError
        engine = RetryEngine(retries=3)

        async def fail_permanently():
            raise NonRetryableError("fatal")

        with pytest.raises(NonRetryableError):
            await engine.execute(fail_permanently)
