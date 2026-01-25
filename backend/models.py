"""Database models for PrepAIr using SQLModel."""

import uuid
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class QuestionType(str, Enum):
    OPEN = "open"
    CODE = "code"


class InterviewMode(str, Enum):
    DIRECT = "direct"
    AFTER_CV = "after_cv"


# 1) Users
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    cv_versions: List["CVVersion"] = Relationship(back_populates="user")
    cv_analyses: List["CVAnalysisResult"] = Relationship(back_populates="user")
    sessions: List["InterviewSession"] = Relationship(back_populates="user")
    question_history: List["QuestionHistory"] = Relationship(back_populates="user")
    skill_states: List["UserSkillState"] = Relationship(back_populates="user")
    readiness_snapshots: List["UserReadinessSnapshot"] = Relationship(back_populates="user")


# 2) CV Versions
class CVVersion(SQLModel, table=True):
    __tablename__ = "cv_versions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    cv_text: str
    source: str = Field(default="manual")  # "manual", "improved", etc.
    parent_cv_version_id: Optional[str] = Field(default=None, foreign_key="cv_versions.id")
    
    # Relationships
    user: User = Relationship(back_populates="cv_versions")
    analyses: List["CVAnalysisResult"] = Relationship(back_populates="cv_version")


# 3) CV Analysis Results
class CVAnalysisResult(SQLModel, table=True):
    __tablename__ = "cv_analysis_results"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    cv_version_id: str = Field(foreign_key="cv_versions.id")
    job_spec_id: str = Field(foreign_key="job_specs.id")
    user_id: str = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    match_score: float = Field(default=0.0)  # 0-1
    strengths_json: str = Field(default="[]")  # JSON array
    gaps_json: str = Field(default="[]")  # JSON array
    suggestions_json: str = Field(default="[]")  # JSON array
    focus_json: str = Field(default="{}")  # JSON object
    
    # Relationships
    cv_version: CVVersion = Relationship(back_populates="analyses")
    job_spec: "JobSpec" = Relationship(back_populates="cv_analyses")
    user: User = Relationship(back_populates="cv_analyses")


# 4) Job Specs
class JobSpec(SQLModel, table=True):
    __tablename__ = "job_specs"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    jd_hash: str = Field(index=True, unique=True)
    jd_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    jd_profile_json: Optional[str] = None  # JSON string
    
    # Relationships
    cv_analyses: List[CVAnalysisResult] = Relationship(back_populates="job_spec")
    sessions: List["InterviewSession"] = Relationship(back_populates="job_spec")
    question_history: List["QuestionHistory"] = Relationship(back_populates="job_spec")


# 5) Question Bank
class QuestionBank(SQLModel, table=True):
    __tablename__ = "question_bank"
    
    id: str = Field(primary_key=True)  # "code:123" or "open:456"
    question_type: QuestionType
    difficulty: Optional[str] = None  # "Easy", "Medium", "Hard"
    category: Optional[str] = None
    question_text: str
    topics_json: str = Field(default="[]")  # JSON array
    solution_text: Optional[str] = None
    source: str = Field(default="csv")


# 6) Interview Sessions
class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_sessions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    job_spec_id: str = Field(foreign_key="job_specs.id")
    cv_version_id: Optional[str] = Field(default=None, foreign_key="cv_versions.id")
    mode: InterviewMode
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    plan_json: str = Field(default="{}")  # JSON string
    conversation_state_json: str = Field(default="{}")  # Tracks: current_question_id, followup_count, question_index, etc.
    session_summary_json: Optional[str] = None  # JSON string
    question_start_time: Optional[datetime] = Field(default=None)  # Tracks when current question started
    persona: str = Field(default="friendly")  # Interviewer persona: "friendly", "formal", "challenging"
    language: str = Field(default="english")  # "english", "hebrew"
    
    # Relationships
    user: User = Relationship(back_populates="sessions")
    job_spec: JobSpec = Relationship(back_populates="sessions")
    turns: List["InterviewTurn"] = Relationship(back_populates="session")


# 7) Interview Turns
class InterviewTurn(SQLModel, table=True):
    __tablename__ = "interview_turns"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="interview_sessions.id")
    turn_index: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    question_id: str = Field(foreign_key="question_bank.id")
    question_snapshot: str  # Full question text at time of asking
    user_transcript: str
    user_code: Optional[str] = None
    score_json: str = Field(default="{}")  # JSON object
    topics_json: str = Field(default="[]")  # JSON array
    followup_json: Optional[str] = None  # JSON object or null
    parent_turn_id: Optional[str] = Field(default=None, foreign_key="interview_turns.id")  # Links follow-ups to parent answer
    question_number: int = Field(default=0)  # Question progression (0-based), for backward compatibility
    is_followup: bool = Field(default=False)  # True if this turn is a follow-up to another answer
    time_spent_seconds: int = Field(default=0)  # Time spent on this question
    code_analysis_json: Optional[str] = None  # Code quality analysis from agent
    agent_analysis_json: Optional[str] = None  # Gap analysis from answer analyzer agent
    
    # Relationships
    session: InterviewSession = Relationship(back_populates="turns")


# 8) Question History
class QuestionHistory(SQLModel, table=True):
    __tablename__ = "question_history"
    
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    job_spec_id: str = Field(foreign_key="job_specs.id", primary_key=True)
    question_id: str = Field(foreign_key="question_bank.id", primary_key=True)
    last_asked_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="question_history")
    job_spec: JobSpec = Relationship(back_populates="question_history")


# 9) User Skill State
class UserSkillState(SQLModel, table=True):
    __tablename__ = "user_skill_state"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    topic: str = Field(index=True)
    mastery: float = Field(default=0.0)  # 0-1
    attempts: int = Field(default=0)
    last_score: Optional[float] = None
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="skill_states")


# 10) User Readiness Snapshots
class UserReadinessSnapshot(SQLModel, table=True):
    __tablename__ = "user_readiness_snapshots"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    job_spec_id: Optional[str] = Field(default=None, foreign_key="job_specs.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    readiness_score: float = Field(default=0.0)  # 0-100
    cv_score: float = Field(default=0.0)  # 0-100
    interview_score: float = Field(default=0.0)  # 0-100
    practice_score: float = Field(default=0.0)  # 0-100
    breakdown_json: str = Field(default="{}")  # JSON object
    
    # Relationships
    user: User = Relationship(back_populates="readiness_snapshots")


# 11) Agent Reasoning Traces
class AgentReasoningTrace(SQLModel, table=True):
    """Stores the agent's reasoning trace for each interview turn."""
    __tablename__ = "agent_reasoning_traces"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    turn_id: str = Field(foreign_key="interview_turns.id", index=True)
    session_id: str = Field(foreign_key="interview_sessions.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Reasoning data
    reasoning_json: str = Field(default="[]")  # Full reasoning trace as JSON array
    tool_calls_json: str = Field(default="[]")  # List of tools called
    final_decision: str = Field(default="")  # What agent decided: followup, advance, hint, end
    confidence_score: float = Field(default=0.0)  # Agent's confidence in decision

    # Performance metrics
    total_iterations: int = Field(default=0)  # Number of reasoning iterations
    total_tool_calls: int = Field(default=0)  # Total tools executed
    execution_time_ms: int = Field(default=0)  # Total reasoning time


# 12) Agent Tool Executions
class AgentToolExecution(SQLModel, table=True):
    """Logs each tool execution for debugging and analysis."""
    __tablename__ = "agent_tool_executions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trace_id: str = Field(foreign_key="agent_reasoning_traces.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Tool execution details
    tool_name: str
    tool_args_json: str = Field(default="{}")
    tool_result_json: str = Field(default="{}")
    execution_time_ms: int = Field(default=0)
    success: bool = Field(default=True)
    error_message: Optional[str] = None
