from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import json

DATABASE_URL = "sqlite:///./leads.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class DBLeadStatus(Base):
    __tablename__ = "lead_statuses"

    lead_id = Column(String, primary_key=True, index=True)
    company_name = Column(String)
    email = Column(String)
    
    current_step = Column(String, default="submitted")
    # Store steps_completed as JSON string
    steps_completed_json = Column(String, default="[]")
    
    error_message = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    email_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    quality_score = Column(String, default="{}")
    confidence_level = Column(String, nullable=True)
    confidence_reason = Column(String, nullable=True)
    
    pipeline_step_statuses_json = Column(String, default="{}")
    errors_json = Column(String, default="[]")
    warnings_json = Column(String, default="[]")
    
    is_retry = Column(Boolean, default=False)
    original_lead_id = Column(String, nullable=True)

    @property
    def steps_completed(self) -> list[str]:
        try:
            return json.loads(self.steps_completed_json)
        except Exception:
            return []

    @steps_completed.setter
    def steps_completed(self, val: list[str]):
        self.steps_completed_json = json.dumps(val)

    @property
    def pipeline_step_statuses(self) -> dict:
        try:
            return json.loads(self.pipeline_step_statuses_json)
        except Exception:
            return {}

    @pipeline_step_statuses.setter
    def pipeline_step_statuses(self, val: dict):
        self.pipeline_step_statuses_json = json.dumps(val)

    @property
    def errors(self) -> list:
        try:
            return json.loads(self.errors_json)
        except Exception:
            return []

    @errors.setter
    def errors(self, val: list):
        self.errors_json = json.dumps(val)

    @property
    def warnings(self) -> list:
        try:
            return json.loads(self.warnings_json)
        except Exception:
            return []

    @warnings.setter
    def warnings(self, val: list):
        self.warnings_json = json.dumps(val)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
