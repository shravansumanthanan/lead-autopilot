# Implementation Plan: Production-Grade Resilience and Error Handling

## Overview

This document breaks down the implementation of production-grade resilience and error handling into actionable tasks. Tasks are organized by component and prioritized for incremental delivery.

## Tasks

- [ ] 1. Set up foundation and core infrastructure
  - [x] 1.1 Create Error Categorization System
    - Create `ErrorCategory` enum with all categories (INPUT_VALIDATION, SCRAPING_BLOCKED, etc.)
    - Create `ErrorEvent` Pydantic model with all required fields
    - Implement `ErrorCategorizerService` class with categorization logic
    - Add user-friendly message generation for each error category
    - Add recovery action suggestions for each error category
    - Write unit tests for error categorization
    - Files: `backend/models/errors.py` (new), `backend/services/error_categorizer.py` (new)
    - _Requirements: 14.1, 14.2, 14.6, 20.1, 20.2_

  - [x] 1.2 Implement Retry Engine with Exponential Backoff
    - Create `RetryEngine` class with configurable parameters
    - Implement exponential backoff calculation with jitter
    - Add support for retryable vs non-retryable exceptions
    - Implement Retry-After header extraction for rate limits
    - Create `@with_retry` decorator for easy application
    - Write unit tests for retry logic and backoff calculation
    - Test with simulated failures
    - Files: `backend/utils/retry.py` (enhance existing)
    - _Requirements: 11.1, 11.2, 11.3, 11.5, 11.6_

  - [x] 1.3 Implement Timeout Manager
    - Create `TimeoutManager` class with default timeouts
    - Implement `execute_with_timeout()` method
    - Add environment variable loading for timeout overrides
    - Create `TimeoutContext` context manager
    - Add timeout logging when operations exceed limits
    - Write unit tests for timeout enforcement
    - Files: `backend/utils/timeout.py` (new), `backend/.env.example` (add timeout variables)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

  - [x] 1.4 Implement Circuit Breaker Manager
    - Create `CircuitBreakerState` Pydantic model
    - Create `CircuitBreakerManager` class
    - Implement state transitions (closed → open → half-open → closed)
    - Add failure threshold and timeout configuration
    - Implement `call_with_breaker()` method
    - Add manual force_open/force_close methods
    - Write unit tests for all state transitions
    - Test with simulated service failures
    - Files: `backend/utils/circuit_breaker.py` (new)
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7_


- [x] 11. Implement Metadata-Only Scraper - Create MetadataOnlyScraper class that extracts minimal metadata (domain info, social links, basic contact) when full scraping fails. Create backend/services/metadata_scraper.py. Write unit tests. (Priority: Medium, Effort: 2h)

- [ ] 12. Create Resilient Scraper Service with Fallbacks - Create ResilientScraperService class with scrape_with_fallbacks() method implementing fallback hierarchy (Firecrawl → Basic → Playwright → Metadata), circuit breaker integration, retry logic, 30-second timeout, and warnings list. Create backend/services/resilient_scraper.py. Write integration tests. (Priority: High, Effort: 4h, Dependencies: Tasks 2, 3, 4, 10, 11)

- [ ] 13. Integrate Resilient Scraper into Pipeline - Update report_pipeline.py to use ResilientScraperService, handle warnings, store errors, and update quality score. Test with various failure scenarios. (Priority: High, Effort: 2h, Dependencies: Task 12)

- [ ] 14. Implement Schema Validation for AI Outputs - Enhance AIAnalysis Pydantic model with strict validation, field validators for minimum content length, validators for required list items, and validation error messages. Update backend/models.py. Write unit tests. (Priority: High, Effort: 2h)

- [ ] 15. Implement Fallback Content Generator - Create FallbackContentGenerator class with industry-specific templates (5+ industries), generate_fallback_analysis(), generate_executive_summary(), generate_swot_from_metadata(), and generate_action_roadmap() methods. Create backend/services/fallback_generator.py and template JSON files. Write unit tests. (Priority: High, Effort: 4h)

- [ ] 16. Implement Repetitive Content Detection - Create ContentValidator class with detect_repetitive_content() method to detect same sentence repeated 3+ times and paragraph-level repetition. Create backend/services/content_validator.py. Write unit tests. (Priority: Medium, Effort: 2h)

- [ ] 17. Create Resilient AI Analysis Service - Create ResilientAIAnalysisService class with analyze_with_validation() method, schema validation, retry logic for invalid JSON (2 retries), circuit breaker integration, 45-second timeout, rate limit handling, repetitive content detection, and fallback to FallbackContentGenerator. Create backend/services/resilient_ai_analysis.py. Write integration tests. (Priority: High, Effort: 5h, Dependencies: Tasks 2, 3, 4, 14, 15, 16)

- [ ] 18. Integrate Resilient AI Analysis into Pipeline - Update report_pipeline.py to use ResilientAIAnalysisService, handle warnings, store errors, and update quality score. Test with various AI failure scenarios. (Priority: High, Effort: 2h, Dependencies: Task 17)

- [ ] 19. Implement PDF Validation - Create PDFValidator class with validate_pdf() method to check file size, verify PDF header magic bytes, and attempt to open with PyPDF2. Create backend/services/pdf_validator.py. Add PyPDF2 to requirements.txt. Write unit tests. (Priority: Medium, Effort: 2h)

- [ ] 20. Implement Markdown Report Generator - Create MarkdownReportGenerator class with generate_markdown_report() method, markdown template with all sections, confidence indicators, and formatted data tables. Create backend/services/markdown_generator.py and backend/templates/report_template.md. Write unit tests. (Priority: Medium, Effort: 3h)

  - [x] 1.5 Create Quality Score Calculator
    - Create `QualityScoreComponents` Pydantic model
    - Create `QualityScoreCalculator` class
    - Implement `_score_scraped_data()` with weighted scoring
    - Implement `_score_ai_analysis()` with weighted scoring
    - Implement `_score_web_search()` scoring
    - Implement `calculate_score()` to combine all scores
    - Write unit tests with various data completeness scenarios
    - Verify scoring weights sum to 1.0
    - Files: `backend/models/quality.py` (new), `backend/services/quality_scorer.py` (new)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 1.6 Create Confidence Level Assigner
    - Create `ConfidenceLevel` enum (High/Medium/Low)
    - Create `ConfidenceMetadata` Pydantic model
    - Create `ConfidenceLevelAssigner` class
    - Implement threshold-based confidence assignment
    - Implement `_generate_confidence_reason()` with clear explanations
    - Implement `_identify_missing_sources()` and `_identify_available_sources()`
    - Write unit tests for all confidence levels
    - Test edge cases (score exactly at thresholds)
    - Files: `backend/models/quality.py` (enhance), `backend/services/confidence_assigner.py` (new)
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [x] 1.7 Enhance Database Models for Tracking
    - Add `quality_score` JSON field to Lead model
    - Add `confidence_level` and `confidence_reason` fields to Lead model
    - Add `pipeline_step_statuses` JSON field for detailed tracking
    - Add `errors` JSON field for error event storage
    - Add `warnings` JSON field for warning messages
    - Add `is_retry` and `original_lead_id` fields for idempotency
    - Create database migration
    - Update Lead model in `models.py`
    - Files: `backend/models.py` (enhance Lead model), `backend/alembic/versions/xxx_add_resilience_fields.py` (new migration)
    - _Requirements: 16.1, 16.2, 16.3_

- [ ] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement input validation and normalization
  - [x] 3.1 Implement Input Validation Service
    - Create `InputValidationService` class
    - Implement email validation using RFC 5322 rules
    - Implement URL normalization (add https://, fix common typos)
    - Implement text input sanitization
    - Implement duplicate submission detection
    - Add validation that never rejects (always proceeds with warnings)
    - Write unit tests for all validation scenarios
    - Test with malformed inputs
    - Files: `backend/services/input_validator.py` (new), `backend/requirements.txt` (add `email-validator` library)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Foundation tasks (1.1-1.7) must be completed before other components
- Resilient services (scraper, AI analysis, PDF generation) build on foundation components
- Integration tasks wire resilient services into the main pipeline
- Health monitoring and observability tasks can be implemented in parallel with core features

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "3.1"]
    },
    {
      "id": 1,
      "tasks": ["11", "14", "15", "16", "19", "20"]
    },
    {
      "id": 2,
      "tasks": ["12", "17"]
    },
    {
      "id": 3,
      "tasks": ["13", "18"]
    }
  ]
}
```

