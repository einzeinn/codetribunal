"""
CodeTribunal - Database Module
Neon PostgreSQL (via SQLAlchemy) for storing cases, proceedings, and verdicts.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from dotenv import load_dotenv
import os

from .config import settings

load_dotenv()
logger = logging.getLogger("codetribunal.database")

# ═════════════════════════════════════════════════════════════════════
# SQLAlchemy Engine & Session (Neon PostgreSQL)
# ═════════════════════════════════════════════════════════════════════
DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    # Ensure SQLAlchemy uses psycopg3 driver
    sa_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    try:
        engine = create_engine(
            sa_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("SQLAlchemy engine connected to Neon PostgreSQL.")
    except Exception as e:
        logger.error(f"Could not initialize SQLAlchemy engine: {e}")


# ═════════════════════════════════════════════════════════════════════
# ORM Models
# ═════════════════════════════════════════════════════════════════════
class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    code_content = Column(Text)
    language = Column(String)
    concern = Column(String, default="")
    status = Column(String, default="pending")  # pending | in_progress | completed
    created_at = Column(DateTime, default=datetime.utcnow)

    proceedings = relationship("Proceeding", back_populates="case", cascade="all, delete-orphan")
    verdict = relationship("Verdict", back_populates="case", uselist=False, cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "language": self.language,
            "concern": self.concern, "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Proceeding(Base):
    __tablename__ = "proceedings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    agent = Column(String)     # AEGIS, ARBITER, AXIOM, METRIC, LEDGER
    tag = Column(String)       # Opening, Objection, Evidence, etc.
    message = Column(Text)
    round_number = Column(Integer)
    confidence = Column(Float, default=1.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="proceedings")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "case_id": self.case_id, "agent": self.agent,
            "tag": self.tag, "message": self.message,
            "round_number": self.round_number, "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class Verdict(Base):
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    security_score = Column(Float)
    performance_score = Column(Float)
    maintainability_score = Column(Float)
    summary = Column(Text)
    recommendations = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="verdict")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "case_id": self.case_id,
            "security_score": self.security_score,
            "performance_score": self.performance_score,
            "maintainability_score": self.maintainability_score,
            "summary": self.summary, "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Session(Base):
    """
    Neon-backed session store replacing the in-memory dict.
    Solves multi-worker state sharing (ECS / serverless deployments).
    Payload is stored as JSONB for flexible schema.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)           # UUID string
    payload = Column(JSONB, nullable=False)          # {code_content, language, focus_area, title, filename}
    created_at = Column(DateTime, default=datetime.utcnow)
    consumed = Column(String, default="pending")     # pending | consumed


# ═════════════════════════════════════════════════════════════════════
# Session Dependency
# ═════════════════════════════════════════════════════════════════════
def get_db():
    """FastAPI dependency for DB sessions."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Check DATABASE_URL.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    if engine:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured.")
    else:
        logger.warning("Cannot init DB: engine not available.")


# ═════════════════════════════════════════════════════════════════════
# CRUD Helpers (sync, used with SQLAlchemy sessions)
# ═════════════════════════════════════════════════════════════════════
def create_case(db, title: str, code_content: str, language: str, concern: str = "") -> Case:
    case = Case(title=title, code_content=code_content, language=language, concern=concern)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def save_proceeding(db, case_id: int, agent: str, tag: str, message: str,
                    round_number: int, confidence: float = 1.0) -> Proceeding:
    proc = Proceeding(
        case_id=case_id, agent=agent, tag=tag, message=message,
        round_number=round_number, confidence=confidence,
    )
    db.add(proc)
    db.commit()
    return proc


def save_verdict(db, case_id: int, security_score: float, performance_score: float,
                 maintainability_score: float, summary: str, recommendations: str = "") -> Verdict:
    verdict = Verdict(
        case_id=case_id, security_score=security_score,
        performance_score=performance_score, maintainability_score=maintainability_score,
        summary=summary, recommendations=recommendations,
    )
    db.add(verdict)
    db.commit()
    db.refresh(verdict)
    return verdict


def get_case_by_id(db, case_id: int) -> Optional[Case]:
    return db.query(Case).filter(Case.id == case_id).first()


def list_cases(db, limit: int = 20, offset: int = 0) -> List[Case]:
    return db.query(Case).order_by(Case.created_at.desc()).limit(limit).offset(offset).all()


def update_case_status(db, case_id: int, status: str) -> Optional[Case]:
    case = db.query(Case).filter(Case.id == case_id).first()
    if case:
        case.status = status
        db.commit()
        db.refresh(case)
    return case


# ═════════════════════════════════════════════════════════════════════
# Session CRUD (Neon-backed replacement for in-memory dict)
# ═════════════════════════════════════════════════════════════════════
def create_session(db, session_id: str, payload: Dict[str, Any]) -> Session:
    """Persist a new session to Neon."""
    session = Session(id=session_id, payload=payload, consumed="pending")
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Session {session_id} created in Neon. consumed={session.consumed}")
    return session


def consume_session(db, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Read and atomically consume a session.
    Returns the payload dict or None if not found / already consumed.
    Handles NULL consumed values (legacy DB rows from before column was added).
    """
    session = db.query(Session).filter(
        Session.id == session_id,
        or_(Session.consumed == "pending", Session.consumed.is_(None)),
    ).first()
    if not session:
        logger.info(f"Session {session_id} not found or already consumed.")
        return None
    session.consumed = "consumed"
    db.commit()
    payload = dict(session.payload) if session.payload else {}
    logger.info(f"Session {session_id} consumed from Neon. Payload keys: {list(payload.keys())}")
    return payload


def cleanup_expired_sessions(db, max_age_hours: int = 24) -> int:
    """Delete consumed sessions older than max_age_hours. Returns count deleted."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    deleted = db.query(Session).filter(
        Session.created_at < cutoff,
    ).delete(synchronize_session=False)
    db.commit()
    if deleted:
        logger.info(f"Cleaned up {deleted} expired sessions.")
    return deleted
