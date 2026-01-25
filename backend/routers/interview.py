"""Interview management router."""

import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.db import get_session
from backend.models import (
    User, InterviewSession, InterviewTurn, QuestionBank, QuestionHistory, JobSpec, InterviewMode
)
from backend.schemas import (
    InterviewStartRequest, InterviewStartResponse,
    InterviewNextRequest, InterviewNextResponse,
    InterviewEndRequest, InterviewEndResponse,
    InterviewSkipToCodeRequest
)
from backend.services.selection import build_interview_plan
from backend.services.interview_agent import InterviewAgent


router = APIRouter(prefix="/api/interview", tags=["interview"])


def _get_conversation_state(interview_session) -> Dict[str, Any]:
    """Get current conversation state."""
    state = json.loads(interview_session.conversation_state_json or "{}")
    return {
        "current_question_id": state.get("current_question_id"),
        "followup_count": state.get("followup_count", 0),
        "question_index": state.get("question_index", 0),
        "initial_answer_score": state.get("initial_answer_score", 0),
        "previous_followups": state.get("previous_followups", [])
    }


def _save_conversation_state(interview_session, state: Dict[str, Any], session: Session):
    """Save conversation state."""
    interview_session.conversation_state_json = json.dumps(state)
    session.add(interview_session)
    session.commit()


def _get_last_main_turn(session_id: str, session: Session) -> Optional[InterviewTurn]:
    """Get the last main answer turn (not a followup) for the session."""
    turn = session.exec(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .where(InterviewTurn.is_followup == False)
        .order_by(InterviewTurn.turn_index.desc())
    ).first()
    return turn


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(
    request: InterviewStartRequest,
    session: Session = Depends(get_session)
):
    """Start new interview session."""
    import logging
    logger = logging.getLogger(__name__)
    import traceback
    
    try:
        logger.error(f"[START_INTERVIEW] ===== REQUEST RECEIVED =====")
        logger.error(f"[START_INTERVIEW] user_id={request.user_id}")
        logger.error(f"[START_INTERVIEW] job_spec_id={request.job_spec_id}")
        logger.error(f"[START_INTERVIEW] cv_version_id={request.cv_version_id}")
        logger.error(f"[START_INTERVIEW] mode={request.mode}")
        logger.error(f"[START_INTERVIEW] settings={request.settings}")
        
        user = session.get(User, request.user_id)
        if not user:
            logger.error(f"[START_INTERVIEW] User not found: {request.user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.error(f"[START_INTERVIEW] User found: {user.id}")
        
        job_spec = session.get(JobSpec, request.job_spec_id)
        if not job_spec:
            logger.error(f"[START_INTERVIEW] Job spec not found: {request.job_spec_id}")
            raise HTTPException(status_code=404, detail="Job spec not found")
        
        logger.error(f"[START_INTERVIEW] Job spec found: {job_spec.id}")
        
        # Validate mode
        try:
            mode = InterviewMode(request.mode)
        except ValueError:
            logger.error(f"[START_INTERVIEW] Invalid mode: {request.mode}")
            raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
        
        logger.error(f"[START_INTERVIEW] Building interview plan...")
        # Build interview plan
        plan_json = build_interview_plan(
            request.user_id,
            request.job_spec_id,
            request.cv_version_id,
            request.mode,
            request.settings,
            session
        )
        logger.error(f"[START_INTERVIEW] Plan built successfully")
        
        # Create interview session
        # Get persona from settings (supports both dict and Pydantic model)
        settings_dict = request.settings.model_dump() if hasattr(request.settings, 'model_dump') else request.settings
        persona = settings_dict.get("persona", "friendly") if isinstance(settings_dict, dict) else "friendly"
        language = settings_dict.get("language", "english") if isinstance(settings_dict, dict) else "english"
        
        interview_session = InterviewSession(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            job_spec_id=request.job_spec_id,
            cv_version_id=request.cv_version_id,
            mode=mode,
            plan_json=json.dumps(plan_json),
            conversation_state_json=json.dumps({
                "current_question_id": None,
                "followup_count": 0,
                "question_index": 0,
                "initial_answer_score": 0,
                "previous_followups": []
            }),
            question_start_time=datetime.utcnow(),
            persona=persona,
            language=language
        )
        session.add(interview_session)
        session.commit()
        session.refresh(interview_session)
        
        logger.error(f"[START_INTERVIEW] Created session: {interview_session.id}")
        
        # Get first question
        plan_items = plan_json.get("items", [])
        if not plan_items:
            logger.error("[START_INTERVIEW] Interview plan is empty")
            raise HTTPException(status_code=500, detail="Interview plan is empty")
        
        first_item = plan_items[0]
        first_question_id = first_item.get("selected_question_id")
        first_question = session.get(QuestionBank, first_question_id)
        
        if not first_question:
            logger.error(f"[START_INTERVIEW] First question not found: {first_question_id}")
            raise HTTPException(status_code=500, detail="First question not found")
        
        logger.error(f"[START_INTERVIEW] First question: {first_question.question_text[:50]}...")
        
        # Record question history
        history = QuestionHistory(
            user_id=request.user_id,
            job_spec_id=request.job_spec_id,
            question_id=first_question_id
        )
        session.add(history)
        session.commit()
        
        # Plan summary
        plan_summary = {
            "total": plan_json.get("total", 0),
            "sections": plan_json.get("sections", [])
        }
        
        # Translate AND REFINE first question
        first_question_text = first_question.question_text
        
        # Use the agent's refiner for consistent quality
        from backend.services.interview_agent import AgenticInterviewAgent
        temp_agent = AgenticInterviewAgent()
        first_question_text = temp_agent._refine_and_translate(
            first_question.question_text, 
            first_item.get("type", "open"), 
            language
        )
        logger.error(f"[START_INTERVIEW] Refined/translated first question: {first_question_text[:80]}...")
        
        # Store the refined question in state for consistency
        state_dict = json.loads(interview_session.conversation_state_json or "{}")
        state_dict["refined_q_0"] = first_question_text
        interview_session.conversation_state_json = json.dumps(state_dict)
        session.add(interview_session)
        session.commit()
        
        # First question data
        first_question_data = {
            "question_id": first_question.id,
            "text": first_question_text,
            "type": first_item.get("type", "open"),
            "topics": json.loads(first_question.topics_json or "[]")
        }
        
        logger.error(f"[START_INTERVIEW] SUCCESS - Session ready")
        
        return InterviewStartResponse(
            session_id=interview_session.id,
            plan_summary=plan_summary,
            first_question=first_question_data,
            total_questions=plan_json.get("total", 0)
        )
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"[START_INTERVIEW] EXCEPTION: {str(e)}")
        logger.error(f"[START_INTERVIEW] TRACEBACK: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Interview start failed: {str(e)}")


@router.post("/next", response_model=InterviewNextResponse)
def next_interview_step(
    request: InterviewNextRequest,
    session: Session = Depends(get_session)
):
    """
    Process answer and manage multi-turn conversation flow.
    
    Flow:
    1. If followup_count == 0: New answer to a question
       - Score it, decide if followup needed
       - If yes: generate followup, don't advance question
       - If no: move to next question
    
    2. If followup_count > 0: Answer to a followup
       - Score it, compare with previous answer
       - Decide if another followup or move on
    """
    interview_session = session.get(InterviewSession, request.session_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    if interview_session.ended_at:
        raise HTTPException(status_code=400, detail="Interview session already ended")
    
    # Get plan
    plan = json.loads(interview_session.plan_json or "{}")
    plan_items = plan.get("items", [])
    
    # Get job spec for role profile
    job_spec = session.get(JobSpec, interview_session.job_spec_id)
    role_profile = json.loads(job_spec.jd_profile_json) if job_spec and job_spec.jd_profile_json else {}
    
    agent = InterviewAgent()
    result = agent.process_turn(
        request=request,
        interview_session=interview_session,
        plan_items=plan_items,
        role_profile=role_profile,
        session=session
    )

    return InterviewNextResponse(**result)


@router.post("/end", response_model=InterviewEndResponse)
def end_interview(
    request: InterviewEndRequest,
    session: Session = Depends(get_session)
):
    """End interview session."""
    interview_session = session.get(InterviewSession, request.session_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    interview_session.ended_at = datetime.utcnow()
    
    # Generate session summary (simplified)
    turns = session.exec(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == request.session_id)
        .order_by(InterviewTurn.turn_index)
    ).all()
    
    summary = {
        "total_turns": len(turns),
        "completed_at": interview_session.ended_at.isoformat()
    }
    
    interview_session.session_summary_json = json.dumps(summary)
    session.add(interview_session)
    session.commit()
    
    # Compute readiness snapshot
    from backend.services.readiness import compute_readiness_snapshot
    compute_readiness_snapshot(
        session, interview_session.user_id, interview_session.job_spec_id, context="interview_end"
    )
    
    return InterviewEndResponse(ok=True)


@router.get("/history/{user_id}")
def get_interview_history(
    user_id: str,
    session: Session = Depends(get_session)
):
    """Get list of past interviews for a user."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all interview sessions for this user
    sessions = session.exec(
        select(InterviewSession)
        .where(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
    ).all()
    
    history = []
    for interview_session in sessions:
        # Get turn count and average score
        turns = session.exec(
            select(InterviewTurn)
            .where(InterviewTurn.session_id == interview_session.id)
        ).all()
        
        total_score = 0.0
        for turn in turns:
            score_data = json.loads(turn.score_json or "{}")
            total_score += score_data.get("overall", 0.0)
        
        avg_score = (total_score / len(turns) * 100) if turns else 0.0
        
        # Get job spec for role info
        job_spec = session.get(JobSpec, interview_session.job_spec_id)
        role_title = "Unknown Role"
        if job_spec and job_spec.jd_profile_json:
            profile = json.loads(job_spec.jd_profile_json)
            role_title = profile.get("role_title", "Unknown Role")
        
        history.append({
            "session_id": interview_session.id,
            "role_title": role_title,
            "mode": interview_session.mode.value,
            "created_at": interview_session.created_at.isoformat(),
            "ended_at": interview_session.ended_at.isoformat() if interview_session.ended_at else None,
            "is_completed": interview_session.ended_at is not None,
            "questions_answered": len(turns),
            "average_score": round(avg_score, 1)
        })
    
    return {"interviews": history}


@router.get("/session/{session_id}")
def get_session_data(
    session_id: str,
    session: Session = Depends(get_session)
):
    """Get full interview session including turns."""
    interview_session = session.get(InterviewSession, session_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    # Get turns
    turns = session.exec(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.turn_index)
    ).all()
    
    turns_data = []
    for turn in turns:
        turns_data.append({
            "id": turn.id,
            "turn_index": turn.turn_index,
            "question_id": turn.question_id,
            "question_snapshot": turn.question_snapshot,
            "user_transcript": turn.user_transcript,
            "user_code": turn.user_code,
            "score_json": json.loads(turn.score_json or "{}"),
            "topics_json": json.loads(turn.topics_json or "[]"),
            "followup_json": json.loads(turn.followup_json) if turn.followup_json else None,
            "created_at": turn.created_at.isoformat()
        })
    
    return {
        "id": interview_session.id,
        "user_id": interview_session.user_id,
        "job_spec_id": interview_session.job_spec_id,
        "mode": interview_session.mode.value,
        "created_at": interview_session.created_at.isoformat(),
        "ended_at": interview_session.ended_at.isoformat() if interview_session.ended_at else None,
        "plan_json": json.loads(interview_session.plan_json or "{}"),
        "session_summary_json": json.loads(interview_session.session_summary_json) if interview_session.session_summary_json else None,
        "turns": turns_data
    }


@router.post("/skip-to-code", response_model=InterviewNextResponse)
async def skip_to_code(request: InterviewSkipToCodeRequest, session: Session = Depends(get_session)):
    """Force skip to the first coding question in the plan."""
    interview_session = session.get(InterviewSession, request.session_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    plan_json = json.loads(interview_session.plan_json or "{}")
    items = plan_json.get("items", [])
    
    # Find first coding question
    code_index = -1
    for i, item in enumerate(items):
        if item.get("type") == "code":
            code_index = i
            break
            
    if code_index == -1:
        # No coding questions found
        raise HTTPException(status_code=400, detail="No coding questions in this interview plan")
        
    # Get current state
    state = json.loads(interview_session.conversation_state_json or "{}")
    current_index = state.get("question_index", 0)
    
    # If we are already past or at the coding section, just return current state (or advance)
    # But user specifically asked to skip *to* it.
    
    # Force update state to the coding question
    next_item = items[code_index]
    next_question_id = next_item.get("selected_question_id")
    
    state["question_index"] = code_index
    state["followup_count"] = 0
    state["current_question_id"] = next_question_id
    state["previous_followups"] = []
    
    interview_session.conversation_state_json = json.dumps(state)
    session.add(interview_session)
    session.commit()
    
    # Get next question data (with state to save refined version)
    agent = InterviewAgent()
    next_question_data = agent._agentic._get_next_question_data(
        code_index, 
        items, 
        session, 
        language=interview_session.language or "english",
        interview_session=interview_session,
        state=state
    )
    
    msg_en = "Let's move on to the coding challenge. I'd like to see how you approach a technical problem."
    msg_he = "בוא נעבור לאתגר התכנות. אני רוצה לראות איך אתה ניגש לבעיה טכנית."
    
    message = msg_he if interview_session.language == "hebrew" else msg_en
    
    return {
        "interviewer_message": message,
        "followup_question": None,
        "next_question": next_question_data,
        "is_done": False,
        "progress": {"turn_index": code_index + 1, "total": len(items)},
        "agent_decision": "skip",
        "agent_confidence": 1.0
    }
