"""Agent context manager for maintaining conversation state and memory."""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CandidateProfile:
    """Inferred profile of the candidate based on interview so far."""
    apparent_strengths: List[str] = field(default_factory=list)
    apparent_weaknesses: List[str] = field(default_factory=list)
    communication_style: str = "unknown"  # verbose, concise, technical
    confidence_level: str = "unknown"  # high, medium, low


@dataclass
class SessionMetrics:
    """Metrics about the interview session."""
    hints_given: int = 0
    total_followups: int = 0
    questions_completed: int = 0
    average_score: float = 0.0


@dataclass
class AgentContext:
    """
    Context for the interview agent.

    Contains all information the agent needs to make decisions:
    - Current question and answer
    - Interview history
    - Candidate profile (inferred)
    - Session configuration
    """
    # Current turn info
    session_id: str
    question_id: str
    question_text: str
    question_type: str  # "code", "open", "behavioral"
    question_topics: List[str]

    # Candidate's response
    user_transcript: str
    user_code: Optional[str]

    # Interview state
    question_index: int
    total_questions: int
    followup_count: int
    max_followups: int = 2  # Reduced from 3 to keep interview moving
    previous_followups: List[str] = field(default_factory=list)

    # Interviewer persona
    persona: str = "friendly"  # "friendly", "formal", "challenging"
    language: str = "english"  # "english", "hebrew"

    # Reference materials
    reference_solution: Optional[str] = None
    role_profile: Dict[str, Any] = field(default_factory=dict)

    # Memory
    candidate_profile: CandidateProfile = field(default_factory=CandidateProfile)
    session_metrics: SessionMetrics = field(default_factory=SessionMetrics)

    # Reasoning trace
    observations: List[Dict[str, Any]] = field(default_factory=list)

    def add_observation(self, observation: Dict[str, Any]) -> None:
        """Add a tool result observation to context."""
        self.observations.append({
            "timestamp": datetime.utcnow().isoformat(),
            **observation
        })

    def get_recent_observations(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get the N most recent observations."""
        return self.observations[-n:] if self.observations else []

    def update_candidate_profile(self, analysis: Dict[str, Any]) -> None:
        """Update candidate profile based on analysis."""
        if "strengths" in analysis:
            for s in analysis["strengths"]:
                if s not in self.candidate_profile.apparent_strengths:
                    self.candidate_profile.apparent_strengths.append(s)

        if "gaps" in analysis or "weaknesses" in analysis:
            gaps = analysis.get("gaps", []) + analysis.get("weaknesses", [])
            for g in gaps:
                if g not in self.candidate_profile.apparent_weaknesses:
                    self.candidate_profile.apparent_weaknesses.append(g)

    def to_system_prompt_context(self) -> str:
        """Format context for the agent system prompt."""
        context_parts = [
            f"## Current Question ({self.question_index + 1}/{self.total_questions})",
            f"Type: {self.question_type}",
            f"Topics: {', '.join(self.question_topics)}",
            "",
            "## QUESTION UNDER DISCUSSION (For your context only - DO NOT READ ALOUD)",
            f"{self.question_text}",
            "",
        ]
        
        # Add candidate status explicitly
        has_answer = False
        
        # User Code
        if self.user_code and self.user_code.strip():
            has_answer = True
            context_parts.extend([
                "",
                "## CODE SUBMITTED BY CANDIDATE",
                "IMPORTANT: The candidate has submitted code. You MUST analyze it for correctness, efficiency, and edge cases.",
                f"```",
                self.user_code,
                "```",
            ])
            
        # User Transcript
        if self.user_transcript and self.user_transcript.strip():
            has_answer = True
            context_parts.extend([
                "",
                "## CANDIDATE'S VERBAL EXPLANATION",
                f"Transcript: \"{self.user_transcript}\""
            ])
        else:
            context_parts.append(f"Transcript: (None/Silence - You should prompt them if they are silent)")

        # Explicit instruction if waiting
        if not has_answer:
             context_parts.extend([
                 "",
                 "STATUS: WAITING FOR CANDIDATE. The candidate has NOT submitted an answer yet.",
             ])
        
        context_parts.extend([
            "",
            "## Interview State",
            f"Follow-ups on this question: {self.followup_count}/{self.max_followups}",
        ])

        if self.previous_followups:
            context_parts.append("Previous follow-ups asked:")
            for fu in self.previous_followups:
                context_parts.append(f"  - {fu}")

        if self.observations:
            context_parts.extend([
                "",
                "## Recent Analysis Results",
            ])
            for obs in self.get_recent_observations(2):
                tool = obs.get("tool", "unknown")
                result = obs.get("result", {})
                if isinstance(result, dict):
                    score = result.get("score", "N/A")
                    context_parts.append(f"- {tool}: score={score}")

        if self.candidate_profile.apparent_strengths or self.candidate_profile.apparent_weaknesses:
            context_parts.extend([
                "",
                "## Candidate Profile (so far)",
                f"Strengths: {', '.join(self.candidate_profile.apparent_strengths[:3]) or 'unknown'}",
                f"Areas to probe: {', '.join(self.candidate_profile.apparent_weaknesses[:3]) or 'unknown'}",
            ])

        role_level = self.role_profile.get("experience_level", "mid")
        context_parts.extend([
            "",
            f"## Role: {self.role_profile.get('role_title', 'Software Engineer')} ({role_level} level)",
        ])

        return "\n".join(context_parts)

    def should_force_advance(self) -> bool:
        """Check if we must advance regardless of answer quality."""
        return self.followup_count >= self.max_followups

    def is_last_question(self) -> bool:
        """Check if this is the last question."""
        return self.question_index >= self.total_questions - 1


def build_context_from_request(
    session_id: str,
    question: Any,  # QuestionBank model
    request: Any,   # InterviewNextRequest
    plan_items: List[Dict[str, Any]],
    role_profile: Dict[str, Any],
    state: Dict[str, Any],
    persona: str = "friendly",
    language: str = "english"
) -> AgentContext:
    """Build an AgentContext from request and database objects."""
    question_type = "open"
    if hasattr(question, "question_type") and question.question_type:
        question_type = question.question_type.value

    topics = []
    if hasattr(question, "topics_json") and question.topics_json:
        topics = json.loads(question.topics_json)

    reference_solution = None
    if question_type == "code" and hasattr(question, "solution_text"):
        reference_solution = question.solution_text

    return AgentContext(
        session_id=session_id,
        question_id=question.id,
        question_text=question.question_text,
        question_type=question_type,
        question_topics=topics,
        user_transcript=request.user_transcript or "",
        user_code=request.user_code,
        question_index=state.get("question_index", 0),
        total_questions=len(plan_items),
        followup_count=state.get("followup_count", 0),
        previous_followups=state.get("previous_followups", []),
        persona=persona,
        language=language,
        reference_solution=reference_solution,
        role_profile=role_profile,
    )
