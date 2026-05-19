"""
PDF Generator Module.

Renders the Jinja2 HTML report template with enriched company data
and converts it to a professional PDF using WeasyPrint.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from core_models import EnrichedCompanyData

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def _ensure_output_dir() -> Path:
    """Ensure the output directory exists."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


# ── Public API ───────────────────────────────────────────────────────────────

def generate_report_pdf(enriched: EnrichedCompanyData) -> str:
    """
    Generate a professional PDF report from enriched company data.

    Args:
        enriched: The complete enriched company data.

    Returns:
        Absolute path to the generated PDF file.

    Raises:
        Exception: If PDF generation fails critically.
    """
    output_dir = _ensure_output_dir()

    # Build safe filename
    safe_name = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in enriched.lead.company
    ).strip("_")[:50]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_{timestamp}.pdf"
    pdf_path = output_dir / filename

    logger.info(f"Generating PDF report: {filename}")

    # Theme selection based on industry
    industry_lower = enriched.lead.industry.lower()
    
    themes = {
        "finance": {"bg": "#064e3b", "primary": "#059669", "light": "#d1fae5", "accent": "#10b981"},
        "consulting": {"bg": "#064e3b", "primary": "#059669", "light": "#d1fae5", "accent": "#10b981"},
        "tech": {"bg": "#1e1b4b", "primary": "#4338ca", "light": "#e0e7ff", "accent": "#6366f1"},
        "software": {"bg": "#1e1b4b", "primary": "#4338ca", "light": "#e0e7ff", "accent": "#6366f1"},
        "saas": {"bg": "#1e1b4b", "primary": "#4338ca", "light": "#e0e7ff", "accent": "#6366f1"},
        "healthcare": {"bg": "#134e4a", "primary": "#0d9488", "light": "#ccfbf1", "accent": "#14b8a6"},
        "medical": {"bg": "#134e4a", "primary": "#0d9488", "light": "#ccfbf1", "accent": "#14b8a6"},
        "marketing": {"bg": "#7f1d1d", "primary": "#dc2626", "light": "#fee2e2", "accent": "#ef4444"},
        "design": {"bg": "#7f1d1d", "primary": "#dc2626", "light": "#fee2e2", "accent": "#ef4444"},
    }
    
    # Default fallback theme
    theme = {"bg": "#1e3a8a", "primary": "#2563eb", "light": "#dbeafe", "accent": "#3b82f6"}
    
    for key, val in themes.items():
        if key in industry_lower:
            theme = val
            break

    # Load and render template
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("report.html")

    # Prepare template context
    context = {
        "theme": theme,
        "company_name": enriched.lead.company,
        "industry": enriched.lead.industry,
        "website": enriched.lead.website,
        "company_size": enriched.lead.company_size,
        "report_date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "quality_score": enriched.data_quality_score,
        "scraped": enriched.scraped,
        "analysis": enriched.analysis,
        # Business branding from env
        "business_name": os.getenv("BUSINESS_NAME", "Lead Autopilot"),
        "business_tagline": os.getenv("BUSINESS_TAGLINE", "Data-Driven Insights"),
        "business_email": os.getenv("BUSINESS_EMAIL", "contact@example.com"),
        "business_phone": os.getenv("BUSINESS_PHONE", ""),
        "business_website": os.getenv("BUSINESS_WEBSITE", ""),
    }

    html_content = template.render(**context)

    # Generate PDF with WeasyPrint
    try:
        html = HTML(string=html_content, base_url=str(TEMPLATE_DIR))
        html.write_pdf(str(pdf_path))
        file_size = pdf_path.stat().st_size
        logger.info(f"PDF generated: {pdf_path} ({file_size:,} bytes)")
        return str(pdf_path)
    except Exception as e:
        logger.error(f"WeasyPrint failed: {e}. Falling back to markdown backup.")
        return _generate_markdown_backup(enriched, output_dir, safe_name, timestamp)

def _generate_markdown_backup(enriched: EnrichedCompanyData, output_dir: Path, safe_name: str, timestamp: str) -> str:
    """Generate a markdown version of the report if PDF fails."""
    md_filename = f"{safe_name}_{timestamp}_fallback.md"
    md_path = output_dir / md_filename
    
    content = f"# Business Intelligence Report: {enriched.lead.company}\n\n"
    content += f"**Industry**: {enriched.lead.industry}\n"
    content += f"**Website**: {enriched.lead.website}\n"
    content += f"**Confidence Level**: {enriched.confidence_level} ({enriched.confidence_reason})\n\n"
    
    content += "## Executive Summary\n"
    content += f"{enriched.analysis.executive_summary}\n\n"
    
    content += "## Current State Assessment\n"
    content += f"{enriched.analysis.current_state_assessment}\n\n"
    
    content += "## SWOT Analysis\n"
    content += f"- **Strengths**: {', '.join(enriched.analysis.swot.strengths)}\n"
    content += f"- **Weaknesses**: {', '.join(enriched.analysis.swot.weaknesses)}\n"
    content += f"- **Opportunities**: {', '.join(enriched.analysis.swot.opportunities)}\n"
    content += f"- **Threats**: {', '.join(enriched.analysis.swot.threats)}\n\n"
    
    content += "## Action Roadmap\n"
    for item in enriched.analysis.action_roadmap:
        content += f"- **{item.timeline}**: {item.recommendation} (Impact: {item.impact}, Effort: {item.effort})\n"
        
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    logger.info(f"Markdown fallback generated: {md_path}")
    return str(md_path)
