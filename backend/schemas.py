"""
CodeTribunal - Pydantic Schemas
Data validation schemas for API requests and responses
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    """Enumeration of agent roles in the tribunal"""
    AEGIS = "AEGIS"      # Prosecutor - Security hunter
    ARBITER = "ARBITER"  # Judge - Orchestrator
    AXIOM = "AXIOM"      # Defense - Code defender
    METRIC = "METRIC"    # Expert - Metrics analyst
    LEDGER = "LEDGER"    # Clerk - Record keeper


class ProceedingEntryBase(BaseModel):
    """Base schema for a proceeding entry"""
    agent: AgentRole
    tag: str  # e.g., "Opening", "Objection", "Evidence", "Sustained", etc.
    message: str
    round_number: int
    confidence: float = 1.0


class ProceedingEntryCreate(ProceedingEntryBase):
    """Schema for creating a new proceeding entry"""
    case_id: int


class ProceedingEntry(ProceedingEntryBase):
    """Schema for a proceeding entry response"""
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class CaseBase(BaseModel):
    """Base schema for a case"""
    title: str
    language: str = "unknown"
    concern: Optional[str] = ""


class CaseCreate(CaseBase):
    """Schema for creating a new case"""
    code_content: str


class CaseUpdate(BaseModel):
    """Schema for updating a case"""
    status: Optional[str] = None


class Case(CaseBase):
    """Schema for a case response"""
    id: int
    status: str
    created_at: datetime
    proceedings: List[ProceedingEntry] = []

    class Config:
        from_attributes = True


class VerdictBase(BaseModel):
    """Base schema for a verdict"""
    security_score: float
    performance_score: float
    maintainability_score: float
    summary: str
    recommendations: Optional[str] = ""


class VerdictCreate(VerdictBase):
    """Schema for creating a verdict"""
    case_id: int


class Verdict(VerdictBase):
    """Schema for a verdict response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CodeSubmission(BaseModel):
    """Request model for code submission"""
    code_content: str
    language: str = "unknown"
    focus_area: str = ""


class ProceedingResponse(BaseModel):
    """Response model for individual proceedings"""
    agent: str
    tag: str
    message: str
    round_number: int
    timestamp: str
    confidence: float


class SubmitResponse(BaseModel):
    """Response model for code submission"""
    status: str
    proceedings: List[ProceedingResponse]
    summary: str


class TokenUsage(BaseModel):
    """Schema for tracking token usage"""
    input_tokens: int
    output_tokens: int
    model_name: str
    timestamp: datetime


class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str
    message: str
    timestamp: datetime