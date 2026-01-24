"""Pydantic schemas for API requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# User schemas
class UserEnsureRequest(BaseModel):
    user_id: Optional[str] = Field(None, max_length=100)

class UserEnsureResponse(BaseModel):
    user_id: str


# CV schemas
class CVIngestRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    cv_text: str = Field(..., min_length=50, max_length=50000)
    
    @field_validator('cv_text')
    @classmethod
    def validate_cv_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('CV text cannot be empty')
        return v.strip()


class CVIngestResponse(BaseModel):
    cv_version_id: str
    cv_profile_json: Optional[Dict[str, Any]] = None


class CVAnalyzeRequest(BaseModel):
    user_id: str
    cv_version_id: str
    job_spec_id: str


class CVAnalyzeResponse(BaseModel):
    match_score: float
    strengths: List[str]
    gaps: List[str]
    suggestions: List[str]
    role_focus: Dict[str, Any]
    cv_text: str


class CVSaveRequest(BaseModel):
    user_id: str
    parent_cv_version_id: Optional[str] = None
    updated_cv_text: str


class CVSaveResponse(BaseModel):
    new_cv_version_id: str


class CVImprovedSection(BaseModel):
    section: str
    original: str
    improved: str
    explanation: str


class CVImprovements(BaseModel):
    improved_sections: List[CVImprovedSection] = []
    new_content_suggestions: List[str] = []
    formatting_tips: List[str] = []


class CVImproveResponse(BaseModel):
    success: bool
    improvements: CVImprovements


# JD schemas
class JDIngestRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    jd_text: str = Field(..., min_length=50, max_length=50000)
    
    @field_validator('jd_text')
    @classmethod
    def validate_jd_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Job description cannot be empty')
        return v.strip()


class JDIngestResponse(BaseModel):
    job_spec_id: str
    jd_hash: str
    jd_profile_json: Optional[Dict[str, Any]] = None


class JDGetResponse(BaseModel):
    id: str
    jd_hash: str
    jd_text: str
    created_at: datetime
    jd_profile_json: Optional[Dict[str, Any]] = None


# Interview schemas
class InterviewStartRequest(BaseModel):
    user_id: str
    job_spec_id: str
    cv_version_id: Optional[str] = None
    mode: str = "direct"  # "direct" | "after_cv"
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "num_open": 4,
        "num_code": 2,
        "duration_minutes": 12,
        "strict_mode": "realistic"
    })


class InterviewStartResponse(BaseModel):
    session_id: str
    plan_summary: Dict[str, Any]
    first_question: Dict[str, Any]
    total_questions: int


class InterviewNextRequest(BaseModel):
    session_id: str
    user_transcript: str
    user_code: Optional[str] = None
    is_followup: bool = False
    client_metrics: Optional[Dict[str, Any]] = None


class InterviewNextResponse(BaseModel):
    interviewer_message: str
    followup_question: Optional[Dict[str, str]] = None
    next_question: Optional[Dict[str, Any]] = None
    is_done: bool
    progress: Dict[str, int]


class InterviewEndRequest(BaseModel):
    session_id: str


class InterviewEndResponse(BaseModel):
    ok: bool


# Progress schemas
class ProgressOverviewResponse(BaseModel):
    latest_snapshot: Optional[Dict[str, Any]] = None
    trend: List[Dict[str, Any]]
    breakdown: Dict[str, Any]
