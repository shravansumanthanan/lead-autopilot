import json
import os
import logging
from typing import Dict, Any, List

from core_models import AIAnalysis, SWOTAnalysis, ActionItem, Scorecard

logger = logging.getLogger(__name__)

class FallbackContentGenerator:
    """
    Generates structured fallback content for AI analysis when the primary LLM fails.
    Uses industry-specific JSON templates to provide meaningful, generalized insights.
    """

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        self.templates_file = os.path.join(templates_dir, "industry_templates.json")
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """Load templates from disk."""
        if not os.path.exists(self.templates_file):
            logger.warning(f"Templates file not found at {self.templates_file}. Using empty/default internal templates.")
            return {}
        try:
            with open(self.templates_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to parse templates JSON: {e}")
            return {}

    def _get_industry_template(self, industry: str) -> Dict[str, Any]:
        """Fetch the template matching the industry, or fallback to 'default'."""
        if not industry:
            return self.templates.get("default", {})
            
        industry_lower = industry.lower()
        
        # Simple string matching to find nearest template
        for key in self.templates.keys():
            if key != "default" and key in industry_lower:
                return self.templates[key]
                
        return self.templates.get("default", {})

    def generate_executive_summary(self, company_name: str, industry: str, scraped_data: Any) -> str:
        """Generate a generic but professionally formatted executive summary."""
        company = company_name or "The company"
        ind_text = f" in the {industry} sector" if industry else ""
        
        pieces = [f"{company} operates{ind_text}."]
        
        if scraped_data:
            if hasattr(scraped_data, 'title') and scraped_data.title:
                pieces.append(f"Their primary web presence indicates a focus on: '{scraped_data.title}'.")
            if hasattr(scraped_data, 'hero_text') and scraped_data.hero_text:
                pieces.append(f"Core value proposition: {scraped_data.hero_text[:100]}...")
            
        pieces.append("Given the current market dynamics, optimizing digital presence and operational automation presents a significant growth surface.")
        
        # Ensure it meets the 50 char minimum requirement of AIAnalysis validator
        base_text = " ".join(pieces)
        if len(base_text) < 50:
            base_text += " This assessment is generated via baseline heuristics to ensure continuous pipeline operation and resilient reporting."
            
        return base_text
        
    def generate_current_state(self, company_name: str, scraped_data: Any) -> str:
        text = f"{company_name or 'This organization'} maintains an active digital presence but may benefit from modernized workflows."
        if scraped_data and hasattr(scraped_data, 'services') and scraped_data.services:
            text += f" They currently offer {len(scraped_data.services)} documented service areas."
            
        if len(text) < 50:
            text += " Further deep-dive analysis is recommended when advanced AI capabilities are fully restored."
        return text

    def generate_swot_from_metadata(self, template: Dict[str, Any]) -> SWOTAnalysis:
        """Create a SWOT analysis from the industry template."""
        return SWOTAnalysis(
            strengths=template.get("strengths", ["Established presence"]),
            weaknesses=template.get("weaknesses", ["Digital scaling limitations"]),
            opportunities=template.get("opportunities", ["Workflow automation"]),
            threats=template.get("threats", ["Market competition"])
        )

    def generate_action_roadmap(self, template: Dict[str, Any]) -> List[ActionItem]:
        """Generate action items from the template."""
        items_data = template.get("action_roadmap", [
            {"recommendation": "Review Digital Strategy", "timeline": "Immediately", "impact": "High"},
            {"recommendation": "Explore Automation", "timeline": "1-3 months", "impact": "Medium"}
        ])
        
        return [ActionItem(**item) for item in items_data]

    def generate_fallback_analysis(self, company_name: str, industry: str, scraped_data: Any) -> AIAnalysis:
        """
        Main entry point to generate a complete dummy AIAnalysis object.
        """
        template = self._get_industry_template(industry)
        
        return AIAnalysis(
            executive_summary=self.generate_executive_summary(company_name, industry, scraped_data),
            current_state_assessment=self.generate_current_state(company_name, scraped_data),
            swot=self.generate_swot_from_metadata(template),
            action_roadmap=self.generate_action_roadmap(template),
            strategic_opportunities=template.get("strategic_opportunities", ["Service expansion", "Digital upgrading"]),
            risk_areas=template.get("risk_areas", ["Operational scaling", "Competition"]),
            key_findings=[{"category": "General", "observation": "Fallback heuristics successfully applied."}]
        )
