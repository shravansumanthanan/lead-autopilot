# Requirements Document

## Introduction

This document specifies the requirements for transforming the Lead Autopilot system from a "happy-path only" demonstration into a production-grade application with comprehensive resilience, error handling, and graceful degradation capabilities. The system currently generates business analysis reports for companies through web scraping, AI analysis, SEO analysis, PDF generation, email delivery, and Google Sheets integration. The enhancement will ensure the system provides value to users even when individual components fail, maintains data integrity under adverse conditions, and delivers professional error messaging throughout the pipeline.

## Glossary

- **Lead_Autopilot**: The complete lead generation and report delivery system
- **Pipeline**: The sequential workflow from lead submission through report delivery
- **Enrichment_Service**: The component that gathers company data from multiple sources
- **Scraper**: The web scraping component (basic HTTPX+BeautifulSoup or Firecrawl)
- **AI_Analyzer**: The OpenAI-based analysis component that generates insights
- **PDF_Generator**: The component that creates PDF reports from enriched data
- **Email_Service**: The SMTP-based email delivery component
- **Sheets_Logger**: The Google Sheets integration for lead tracking
- **Drive_Uploader**: The Google Drive integration for PDF archival
- **Celery_Worker**: The background task processor for async operations
- **Confidence_Level**: A categorical indicator (High/Medium/Low) of data completeness
- **Quality_Score**: A numerical metric (0.0-1.0) representing data completeness
- **Graceful_Degradation**: The system's ability to provide partial value when components fail
- **Partial_Report**: A report generated with incomplete data but clear confidence indicators

## Requirements

### Requirement 1: Input Validation and Normalization

**User Story:** As a system operator, I want all lead inputs to be validated and normalized, so that downstream components receive clean, consistent data.

#### Acceptance Criteria

1. WHEN a lead submission contains a missing website URL, THE Input_Validator SHALL accept the submission and flag it for company-name-only processing
2. WHEN a lead submission contains a malformed URL, THE Input_Validator SHALL attempt to normalize it by adding the https:// scheme
3. WHEN a lead submission contains an invalid domain format, THE Input_Validator SHALL log a warning and proceed with graceful degradation
4. THE Input_Validator SHALL validate email addresses using RFC 5322 format rules
5. THE Input_Validator SHALL sanitize all text inputs to prevent injection attacks
6. WHEN validation detects a non-existent domain, THE Input_Validator SHALL log the issue and allow the pipeline to continue with business-level analysis

### Requirement 2: Web Scraping Resilience

**User Story:** As a system operator, I want the scraping component to handle failures gracefully, so that temporary website issues do not block report generation.

#### Acceptance Criteria

1. WHEN the primary Firecrawl scraper fails, THE Scraper SHALL automatically fall back to the HTTPX+BeautifulSoup scraper
2. WHEN both scrapers fail due to bot detection, THE Scraper SHALL return an empty ScrapedData object and log the failure
3. WHEN a website requires JavaScript rendering and basic scraping returns minimal content, THE Scraper SHALL attempt Playwright-based rendering
4. WHEN a website is unreachable due to network timeout, THE Scraper SHALL retry up to 3 times with exponential backoff
5. WHEN a website returns a 403/429 status code, THE Scraper SHALL log the blocking event and return partial metadata
6. WHEN scraping yields no content, THE Scraper SHALL extract at least domain metadata and social links from DNS/WHOIS if available
7. THE Scraper SHALL complete within 30 seconds or timeout gracefully

### Requirement 3: AI Analysis Stability

**User Story:** As a system operator, I want AI-generated content to be reliable and structured, so that reports maintain professional quality.

#### Acceptance Criteria

1. THE AI_Analyzer SHALL validate all LLM outputs against a Pydantic schema before returning results
2. WHEN the LLM returns invalid JSON, THE AI_Analyzer SHALL retry the request up to 2 times with schema examples
3. WHEN the LLM output fails schema validation after retries, THE AI_Analyzer SHALL return a minimal AIAnalysis object with a fallback executive summary
4. THE AI_Analyzer SHALL generate analysis in modular sections (executive summary, SWOT, scorecard, action roadmap) rather than a single monolithic prompt
5. WHEN the OpenAI API returns a timeout error, THE AI_Analyzer SHALL retry with exponential backoff up to 3 times
6. WHEN the OpenAI API returns a rate limit error, THE AI_Analyzer SHALL wait for the specified retry-after duration before retrying
7. THE AI_Analyzer SHALL detect and reject outputs containing repetitive text patterns (same sentence repeated 3+ times)
8. WHEN AI analysis fails completely, THE AI_Analyzer SHALL return a professional fallback message indicating limited data availability

### Requirement 4: Graceful Degradation Strategy

**User Story:** As a user, I want to receive a valuable report even when some data sources fail, so that I always get actionable insights.

#### Acceptance Criteria

1. WHEN scraping fails but AI analysis succeeds, THE Pipeline SHALL generate a report with business-level insights and a "Medium" confidence indicator
2. WHEN both scraping and AI analysis fail, THE Pipeline SHALL generate a minimal report with industry context and a "Low" confidence indicator
3. THE Pipeline SHALL calculate a Quality_Score based on the completeness of scraped data, AI analysis, and web search results
4. WHEN the Quality_Score is below 0.4, THE Pipeline SHALL include a prominent disclaimer about data limitations in the report
5. THE Pipeline SHALL never abort completely due to a single component failure
6. WHEN multiple components fail, THE Pipeline SHALL aggregate all available data and generate the best possible Partial_Report
7. THE Pipeline SHALL log all degradation events with specific failure reasons for monitoring

### Requirement 5: Confidence Indicators and Messaging

**User Story:** As a report recipient, I want clear indicators of data quality, so that I understand the reliability of the insights.

#### Acceptance Criteria

1. THE Pipeline SHALL assign a Confidence_Level of "High" when the Quality_Score is 0.8 or above
2. THE Pipeline SHALL assign a Confidence_Level of "Medium" when the Quality_Score is between 0.4 and 0.79
3. THE Pipeline SHALL assign a Confidence_Level of "Low" when the Quality_Score is below 0.4
4. THE PDF_Generator SHALL display the Confidence_Level prominently on the first page of the report
5. THE PDF_Generator SHALL include a confidence_reason field explaining what data was unavailable
6. WHEN a report section is based on limited data, THE PDF_Generator SHALL include an inline disclaimer (e.g., "Based on publicly available information")
7. THE Email_Service SHALL mention the Confidence_Level in the email body when it is not "High"

### Requirement 6: API Failure Handling

**User Story:** As a system operator, I want external API failures to be handled gracefully, so that the system remains operational during service outages.

#### Acceptance Criteria

1. WHEN the OpenAI API is unavailable, THE AI_Analyzer SHALL return a fallback analysis after 3 retry attempts
2. WHEN the Firecrawl API returns a 503 error, THE Scraper SHALL immediately fall back to the basic scraper without retrying
3. WHEN the Serper web search API fails, THE Pipeline SHALL continue with scraped data only and adjust the Quality_Score accordingly
4. WHEN the Google Sheets API fails, THE Sheets_Logger SHALL log the error locally and queue the entry for retry
5. WHEN the Google Drive API fails, THE Drive_Uploader SHALL log the error and continue without blocking email delivery
6. THE Pipeline SHALL implement circuit breaker patterns for external APIs that fail repeatedly (3+ consecutive failures)
7. WHEN an API returns a 429 rate limit error, THE Pipeline SHALL respect the Retry-After header and exponentially back off

### Requirement 7: PDF Generation Resilience

**User Story:** As a system operator, I want PDF generation to handle edge cases gracefully, so that reports are always deliverable.

#### Acceptance Criteria

1. WHEN the PDF_Generator encounters unsupported Unicode characters, THE PDF_Generator SHALL replace them with ASCII equivalents or remove them
2. WHEN HTML-to-PDF rendering fails, THE PDF_Generator SHALL retry with a simplified HTML template
3. WHEN PDF rendering times out after 20 seconds, THE PDF_Generator SHALL fall back to a plain-text markdown report
4. THE PDF_Generator SHALL validate that the generated PDF is not corrupted before returning the file path
5. WHEN PDF generation fails completely, THE PDF_Generator SHALL generate a minimal text-based report as a .txt file
6. THE PDF_Generator SHALL handle malformed HTML gracefully by sanitizing inputs before rendering
7. WHEN the PDF file size exceeds 10MB, THE PDF_Generator SHALL compress images and reduce quality to meet size constraints

### Requirement 8: Email Delivery Reliability

**User Story:** As a user, I want reliable email delivery with retry logic, so that I receive my report even during temporary SMTP issues.

#### Acceptance Criteria

1. WHEN the SMTP server is temporarily unavailable, THE Email_Service SHALL retry delivery up to 3 times with exponential backoff
2. WHEN an email address is invalid, THE Email_Service SHALL log the validation error and mark the lead as "email_failed" in the database
3. WHEN email delivery fails after all retries, THE Email_Service SHALL store the failure reason and notify the system operator
4. THE Email_Service SHALL validate email addresses before attempting delivery
5. WHEN the PDF attachment exceeds the SMTP size limit, THE Email_Service SHALL include a Google Drive download link instead
6. THE Email_Service SHALL use connection pooling to avoid repeated SMTP authentication overhead
7. WHEN email delivery succeeds, THE Email_Service SHALL log the message ID for tracking purposes

### Requirement 9: Async Processing Architecture

**User Story:** As a user, I want immediate feedback when I submit a lead, so that I know my request is being processed without waiting for completion.

#### Acceptance Criteria

1. WHEN a lead is submitted via the API, THE Lead_Autopilot SHALL return a 202 Accepted response with a lead_id within 500ms
2. THE Lead_Autopilot SHALL dispatch the enrichment pipeline to a Celery_Worker for background processing
3. THE Lead_Autopilot SHALL provide a status endpoint that returns the current pipeline step for a given lead_id
4. WHEN the pipeline completes, THE Lead_Autopilot SHALL send an email notification to the user with the report
5. THE Lead_Autopilot SHALL track pipeline progress in the database with timestamps for each completed step
6. WHEN a pipeline step fails, THE Lead_Autopilot SHALL record the error message and current step in the database
7. THE Lead_Autopilot SHALL support polling the status endpoint without blocking other requests

### Requirement 10: Monitoring and Observability

**User Story:** As a system operator, I want comprehensive logging and metrics, so that I can diagnose issues and track system health.

#### Acceptance Criteria

1. THE Lead_Autopilot SHALL log all pipeline steps with timestamps, lead_id, and company name
2. THE Lead_Autopilot SHALL categorize errors into types (scraping_failure, ai_failure, pdf_failure, email_failure, api_timeout)
3. THE Lead_Autopilot SHALL track success/failure rates for each pipeline component in the Sheets_Logger
4. THE Lead_Autopilot SHALL log the Quality_Score and Confidence_Level for every completed report
5. WHEN a component fails, THE Lead_Autopilot SHALL log the full exception traceback for debugging
6. THE Lead_Autopilot SHALL expose a /api/health endpoint that reports the status of all external dependencies
7. THE Lead_Autopilot SHALL log performance metrics (execution time per pipeline step) for optimization analysis

### Requirement 11: Retry Logic and Exponential Backoff

**User Story:** As a system operator, I want intelligent retry logic for transient failures, so that temporary issues do not cause permanent failures.

#### Acceptance Criteria

1. THE Pipeline SHALL implement exponential backoff for all retryable operations (scraping, AI calls, email delivery)
2. THE Pipeline SHALL use a base delay of 1 second and a maximum delay of 10 seconds for retries
3. THE Pipeline SHALL distinguish between retryable errors (timeouts, 503) and non-retryable errors (401, 404)
4. WHEN a retryable operation fails 3 times, THE Pipeline SHALL log the failure and proceed with graceful degradation
5. THE Pipeline SHALL add jitter to retry delays to avoid thundering herd problems
6. THE Pipeline SHALL respect rate limit headers (Retry-After) from external APIs
7. THE Pipeline SHALL not retry operations that are known to be non-idempotent without explicit user confirmation

### Requirement 12: Data Quality Scoring

**User Story:** As a system operator, I want automated data quality scoring, so that I can identify reports that may need manual review.

#### Acceptance Criteria

1. THE Pipeline SHALL calculate a Quality_Score based on the presence of scraped data fields (title, meta_description, about_text, services, tech_stack, social_links, contact_info)
2. THE Pipeline SHALL weight AI analysis completeness (executive_summary, SWOT, action_roadmap, key_findings) at 45% of the total score
3. THE Pipeline SHALL weight scraped data completeness at 40% of the total score
4. THE Pipeline SHALL weight web search context availability at 15% of the total score
5. THE Pipeline SHALL normalize the Quality_Score to a range of 0.0 to 1.0
6. THE Pipeline SHALL store the Quality_Score in the database for each lead
7. WHEN the Quality_Score is below 0.5, THE Pipeline SHALL flag the lead for manual review in the Sheets_Logger

### Requirement 13: Partial Report Generation

**User Story:** As a user, I want to receive a professional report even with incomplete data, so that I always get value from the system.

#### Acceptance Criteria

1. WHEN scraping fails, THE PDF_Generator SHALL generate a report using only AI-inferred business insights
2. WHEN AI analysis fails, THE PDF_Generator SHALL generate a report using only scraped data and metadata
3. THE PDF_Generator SHALL include a "Data Availability" section that lists which data sources were successfully accessed
4. THE PDF_Generator SHALL use professional wording for limitations (e.g., "Limited publicly accessible data" instead of "Scraping failed")
5. WHEN the Quality_Score is below 0.6, THE PDF_Generator SHALL include a disclaimer on the cover page
6. THE PDF_Generator SHALL ensure all report sections are present, even if some contain placeholder text like "Insufficient data for detailed analysis"
7. THE PDF_Generator SHALL maintain consistent formatting and branding regardless of data completeness

### Requirement 14: Error Categorization and Reporting

**User Story:** As a system operator, I want errors to be categorized and reported systematically, so that I can prioritize fixes and improvements.

#### Acceptance Criteria

1. THE Lead_Autopilot SHALL categorize errors into: INPUT_VALIDATION, SCRAPING_BLOCKED, SCRAPING_TIMEOUT, AI_TIMEOUT, AI_INVALID_RESPONSE, PDF_RENDERING, EMAIL_SMTP, API_RATE_LIMIT, API_UNAVAILABLE, UNKNOWN
2. THE Lead_Autopilot SHALL log each error with its category, timestamp, lead_id, and component name
3. THE Lead_Autopilot SHALL aggregate error counts by category in the Sheets_Logger
4. THE Lead_Autopilot SHALL expose error statistics via the /api/health endpoint
5. WHEN a critical error occurs (database unavailable, Celery worker down), THE Lead_Autopilot SHALL send an alert notification
6. THE Lead_Autopilot SHALL include error recovery suggestions in log messages (e.g., "Retry with Playwright" for SCRAPING_BLOCKED)
7. THE Lead_Autopilot SHALL track error trends over time to identify systemic issues

### Requirement 15: Timeout Management

**User Story:** As a system operator, I want all long-running operations to have timeouts, so that the system does not hang indefinitely.

#### Acceptance Criteria

1. THE Scraper SHALL timeout after 30 seconds per website
2. THE AI_Analyzer SHALL timeout after 45 seconds per analysis request
3. THE PDF_Generator SHALL timeout after 20 seconds per rendering operation
4. THE Email_Service SHALL timeout after 15 seconds per SMTP connection
5. THE Pipeline SHALL enforce a total timeout of 120 seconds for the entire enrichment process
6. WHEN a timeout occurs, THE Pipeline SHALL log the timeout event and proceed with graceful degradation
7. THE Pipeline SHALL allow timeout values to be configured via environment variables

### Requirement 16: Idempotency and State Management

**User Story:** As a system operator, I want pipeline operations to be idempotent, so that retries do not cause duplicate reports or data corruption.

#### Acceptance Criteria

1. WHEN a lead is submitted with the same email and company name within 24 hours, THE Lead_Autopilot SHALL return the existing lead_id instead of creating a duplicate
2. THE Pipeline SHALL use the lead_id as an idempotency key for all operations
3. THE Pipeline SHALL track completed steps in the database to avoid re-executing them on retry
4. WHEN a pipeline step is retried, THE Pipeline SHALL skip already-completed steps
5. THE Email_Service SHALL check if an email was already sent before attempting delivery
6. THE Sheets_Logger SHALL use upsert operations to avoid duplicate entries
7. THE Drive_Uploader SHALL check if a file already exists before uploading

### Requirement 17: Fallback Content Generation

**User Story:** As a user, I want the system to generate useful content even when primary data sources fail, so that I always receive actionable insights.

#### Acceptance Criteria

1. WHEN scraping fails, THE AI_Analyzer SHALL generate insights based on the company name and industry alone
2. WHEN AI analysis fails, THE Pipeline SHALL generate a basic report using scraped metadata and industry templates
3. THE Pipeline SHALL maintain a library of industry-specific templates for fallback content
4. WHEN web search fails, THE Pipeline SHALL use cached industry data if available
5. THE Pipeline SHALL include a "Methodology" section in reports explaining which data sources were used
6. WHEN all external data sources fail, THE Pipeline SHALL generate a minimal report with contact information and next steps
7. THE Pipeline SHALL ensure fallback content is clearly marked as "Estimated" or "Inferred"

### Requirement 18: Circuit Breaker Pattern

**User Story:** As a system operator, I want the system to stop calling failing services temporarily, so that we avoid cascading failures and wasted resources.

#### Acceptance Criteria

1. WHEN an external API fails 5 consecutive times, THE Pipeline SHALL open the circuit breaker and stop calling that API for 60 seconds
2. THE Pipeline SHALL track failure counts per API endpoint independently
3. WHEN the circuit breaker is open, THE Pipeline SHALL immediately return a fallback response without attempting the API call
4. AFTER the circuit breaker timeout expires, THE Pipeline SHALL allow one test request to check if the service has recovered
5. WHEN the test request succeeds, THE Pipeline SHALL close the circuit breaker and resume normal operation
6. WHEN the test request fails, THE Pipeline SHALL keep the circuit breaker open and double the timeout duration
7. THE Pipeline SHALL log all circuit breaker state changes (open, half-open, closed) for monitoring

### Requirement 19: Health Check and Dependency Monitoring

**User Story:** As a system operator, I want a comprehensive health check endpoint, so that I can monitor system status and dependencies.

#### Acceptance Criteria

1. THE Lead_Autopilot SHALL expose a /api/health endpoint that returns the status of all external dependencies
2. THE /api/health endpoint SHALL check: OpenRouter API, Firecrawl API, Serper API, SMTP server, Google Sheets API, Google Drive API, Redis, PostgreSQL
3. THE /api/health endpoint SHALL return a 200 status code when all critical dependencies are healthy
4. THE /api/health endpoint SHALL return a 503 status code when any critical dependency is unhealthy
5. THE /api/health endpoint SHALL include response times for each dependency check
6. THE /api/health endpoint SHALL cache health check results for 30 seconds to avoid overwhelming dependencies
7. THE /api/health endpoint SHALL include version information and uptime statistics

### Requirement 20: Professional Error Messaging

**User Story:** As a user, I want error messages to be professional and actionable, so that I understand what happened and what to do next.

#### Acceptance Criteria

1. THE Lead_Autopilot SHALL never expose technical stack traces or internal error codes to end users
2. THE Lead_Autopilot SHALL translate technical errors into user-friendly messages (e.g., "We encountered difficulty accessing the website" instead of "HTTP 403 Forbidden")
3. THE Lead_Autopilot SHALL include next steps in error messages (e.g., "Please verify the website URL and try again")
4. THE Lead_Autopilot SHALL use consistent tone and terminology across all error messages
5. THE Lead_Autopilot SHALL avoid negative language (e.g., "failed", "error", "broken") in user-facing messages when possible
6. THE Lead_Autopilot SHALL provide contact information for support when errors cannot be self-resolved
7. THE Lead_Autopilot SHALL log detailed technical errors internally while showing simplified messages to users
