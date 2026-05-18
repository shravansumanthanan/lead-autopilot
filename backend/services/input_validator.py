import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from database import DBLeadStatus

class InputValidationResult:
    def __init__(self, is_valid: bool, normalized_data: Dict[str, Any], warnings: List[str]):
        self.is_valid = is_valid
        self.normalized_data = normalized_data
        self.warnings = warnings

class InputValidationService:
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session

    def validate_and_normalize(self, input_data: Dict[str, Any]) -> InputValidationResult:
        warnings = []
        normalized = dict(input_data)

        # 1. Email validation and normalization
        email = normalized.get("email", "")
        if email and isinstance(email, str):
            try:
                # Add check_deliverability=False for speed/tests, can be customized
                valid = validate_email(email, check_deliverability=False)
                normalized["email"] = valid.normalized
            except EmailNotValidError as e:
                warnings.append(f"Invalid email format: {str(e)}")
        else:
            warnings.append("Email is missing or empty")

        # 2. URL normalization
        website = normalized.get("website", "")
        if website and isinstance(website, str):
            normalized["website"] = self._normalize_url(website)

        # 3. Text sanitization
        for field in ["name", "company", "message", "industry", "company_size"]:
            if field in normalized and normalized[field]:
                normalized[field] = self._sanitize_text(normalized[field])

        # 4. Duplicate submission detection
        if self.db and email and isinstance(email, str):
            company = normalized.get("company", "")
            if self._is_duplicate(email, company):
                warnings.append("Potential duplicate submission detected")

        # Validation never rejects (always is_valid=True)
        return InputValidationResult(
            is_valid=True,
            normalized_data=normalized,
            warnings=warnings
        )

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url:
            return ""
        
        # Add scheme if missing
        if not re.match(r'^https?://', url):
            url = f"https://{url}"
        
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return url
            
            # Fix common typos in www
            netloc = parsed.netloc
            if netloc.startswith("ww."):
                netloc = "www." + netloc[3:]
            elif netloc.startswith("www,"):
                netloc = "www." + netloc[4:]
            
            # Reconstruct URL
            path = parsed.path if parsed.path else ""
            query = f"?{parsed.query}" if parsed.query else ""
            
            return f"{parsed.scheme}://{netloc}{path}{query}"
        except Exception:
            return url

    def _sanitize_text(self, text: Any) -> Any:
        if not isinstance(text, str):
            return text
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        # Basic HTML stripping
        text = re.sub(r'<[^>]+>', '', text)
        return text

    def _is_duplicate(self, email: str, company: str, hours: int = 24) -> bool:
        """
        Check if the same email (and optionally company) was submitted within the last `hours`.
        """
        if not self.db:
            return False
            
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        stmt = select(DBLeadStatus).where(
            DBLeadStatus.email == email,
            DBLeadStatus.created_at >= time_threshold
        )
        
        if company:
            stmt = stmt.where(DBLeadStatus.company_name == company)
            
        try:
            existing = self.db.execute(stmt).first()
            return existing is not None
        except Exception:
            # If query fails, assume not duplicate to allow processing
            return False
