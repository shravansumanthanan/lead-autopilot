import os
from string import Template
from core_models import EnrichedCompanyData

class MarkdownReportGenerator:
    """Generates markdown reports from EnrichedCompanyData."""

    def __init__(self, template_path: str = None):
        if template_path is None:
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "report_template.md")
        self.template_path = template_path

    def _load_template(self) -> str:
        with open(self.template_path, "r", encoding="utf-8") as f:
            return f.read()

    def generate_markdown_report(self, data: EnrichedCompanyData) -> str:
        """Generate a markdown report from the enriched data."""
        template_content = self._load_template()
        template = Template(template_content)

        # Formatting helper
        def format_list(items):
            return "\n".join([f"  * {item}" for item in items]) if items else "  * None identified"

        # Format SWOT
        swot = data.analysis.swot
        if not swot:
            swot_strengths = format_list([])
            swot_weaknesses = format_list([])
            swot_opportunities = format_list([])
            swot_threats = format_list([])
        elif isinstance(swot, dict):
            swot_strengths = format_list(swot.get("strengths", []))
            swot_weaknesses = format_list(swot.get("weaknesses", []))
            swot_opportunities = format_list(swot.get("opportunities", []))
            swot_threats = format_list(swot.get("threats", []))
        else:
            swot_strengths = format_list(swot.strengths)
            swot_weaknesses = format_list(swot.weaknesses)
            swot_opportunities = format_list(swot.opportunities)
            swot_threats = format_list(swot.threats)

        # Format Action Roadmap
        roadmap_rows = []
        for action in data.analysis.action_roadmap:
            row = f"| {action.recommendation} | {action.timeline} | {getattr(action, 'description', '')} | {getattr(action, 'priority', 'Medium')} | {action.effort} | {action.impact} |"
            roadmap_rows.append(row)
        action_roadmap = "\n".join(roadmap_rows) if roadmap_rows else "| No actions identified | - | - | - | - | - |"

        mapping = {
            "company_name": data.lead.company,
            "date": data.enriched_at.strftime("%Y-%m-%d %H:%M:%S UTC") if data.enriched_at else "Unknown",
            "confidence_level": data.confidence_level,
            "quality_score": f"{data.data_quality_score:.2f}",
            "executive_summary": data.analysis.executive_summary,
            "current_state_assessment": data.analysis.current_state_assessment,
            "swot_strengths": swot_strengths,
            "swot_weaknesses": swot_weaknesses,
            "swot_opportunities": swot_opportunities,
            "swot_threats": swot_threats,
            "key_findings": format_list(data.analysis.key_findings),
            "risk_areas": format_list(data.analysis.risk_areas),
            "strategic_opportunities": format_list(data.analysis.strategic_opportunities),
            "action_roadmap": action_roadmap,
        }

        return template.safe_substitute(mapping)
