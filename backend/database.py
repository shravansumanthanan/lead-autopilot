"""
Database layer for Lead Autopilot.

Key design decisions:
- Native SQLAlchemy JSON columns replace custom Python property serialisation.
  SQLAlchemy transparently handles (de)serialisation; no manual json.loads/dumps.
- The engine is configured for both SQLite (development) and PostgreSQL
  (production).  When DATABASE_URL begins with "postgresql", the engine uses
  connection-pool settings and NullPool for Celery worker sub-processes.
- check_same_thread is only passed for SQLite connections.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ── SQLAlchemy JSON type ──────────────────────────────────────────────────────
# sqlalchemy.types.JSON is natively supported for both SQLite (as TEXT) and
# PostgreSQL (as the native JSONB-compatible JSON type).  It removes the need
# for manual json.loads / json.dumps property wrappers entirely.
from sqlalchemy import JSON

# ── Engine Configuration ──────────────────────────────────────────────────────

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./leads.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_postgres = DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres")

if _is_postgres:
    # PostgreSQL: use a proper connection pool.
    # We use QueuePool for performance, and dispose it on Celery worker init.
    from sqlalchemy.pool import QueuePool

    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        # echo=True,  # Uncomment to log all SQL for debugging
    )
    
    try:
        from celery.signals import worker_process_init
        @worker_process_init.connect
        def dispose_sqlalchemy_engine(**kwargs):
            """
            Dispose of the SQLAlchemy engine in Celery worker processes
            to prevent them from sharing connections across forks.
            """
            engine.dispose()
    except ImportError:
        pass
elif _is_sqlite:
    # SQLite: disable same-thread check (FastAPI runs on multiple threads via
    # Starlette's threadpool; Celery workers also share the file).
    # NOTE: SQLite is fine for development / single-worker use.
    # Migrate to PostgreSQL for any multi-worker production deployment.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Generic fallback for other databases (e.g., MySQL).
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ── ORM Model ─────────────────────────────────────────────────────────────────

class DBLeadStatus(Base):
    """
    Persistent record of a lead's enrichment pipeline state.

    Structured fields (lists, dicts) use SQLAlchemy's JSON column type so
    Python objects are stored and retrieved without manual serialisation code.
    """

    __tablename__ = "lead_statuses"

    lead_id = Column(String, primary_key=True, index=True)
    company_name = Column(String)
    email = Column(String)

    token = Column(String, nullable=True)
    current_step = Column(String, default="submitted")

    # ── Native JSON columns ───────────────────────────────────────────────────
    # SQLAlchemy automatically serialises Python list/dict → database text/JSON
    # and deserialises back on read.  No property wrappers required.
    steps_completed = Column(JSON, default=list, nullable=False)
    pipeline_step_statuses = Column(JSON, default=dict, nullable=False)
    errors = Column(JSON, default=list, nullable=False)
    warnings = Column(JSON, default=list, nullable=False)
    quality_score = Column(JSON, default=dict, nullable=False)

    # ── Scalar fields ─────────────────────────────────────────────────────────
    error_message = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    email_sent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    confidence_level = Column(String, nullable=True)
    confidence_reason = Column(String, nullable=True)

    is_retry = Column(Boolean, default=False)
    original_lead_id = Column(String, nullable=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
