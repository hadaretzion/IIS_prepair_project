"""Interview management router."""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.db import get_session
from backend.models import (
    User, InterviewSession, InterviewTurn, QuestionBank, QuestionHistory, JobSpec, InterviewMode
)
from backend.schemas import (
    InterviewStartRequest, InterviewStartResponse,
    InterviewNextRequest, InterviewNextResponse,
    InterviewEndRequest, InterviewEndResponse
)
from backend.services.selection import build_interview_plan
from backend.services.scoring import score_answer, maybe_generate_followup

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(
    request: InterviewStartRequest,
    session: Session = Depends(get_session)
):
    """Start new interview session."""
    user = session.get(User, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    job_spec = session.get(JobSpec, request.job_spec_id)
    if not job_spec:
        raise HTTPException(status_code=404, detail="Job spec not found")
    
    # Validate mode
    try:
        mode = InterviewMode(request.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    
    # Build interview plan
    plan_json = build_interview_plan(
        request.user_id,
        request.job_spec_id,
        request.cv_version_id,
        request.mode,
        request.settings,
        session
    )
    
    # Create interview session
    interview_session = InterviewSession(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        job_spec_id=request.job_spec_id,
        cv_version_id=request.cv_version_id,
        mode=mode,
        plan_json=json.dumps(plan_json)
    )
    session.add(interview_session)
    session.commit()
    session.refresh(interview_session)
    
    # Get first question
    plan_items = plan_json.get("items", [])
    if not plan_items:
        raise HTTPException(status_code=500, detail="Interview plan is empty")
    
    first_item = plan_items[0]
    first_question_id = first_item.get("selected_question_id")
    first_question = session.get(QuestionBank, first_question_id)
    
    if not first_question:
        raise HTTPException(status_code=500, detail="First question not found")
    
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
    
    # First question data
    first_question_data = {
        "question_id": first_question.id,
        "text": first_question.question_text,
        "type": first_item.get("type", "open"),
        "topics": json.loads(first_question.topics_json or "[]")
    }
    
    return InterviewStartResponse(
        session_id=interview_session.id,
        plan_summary=plan_summary,
        first_question=first_question_data,
        total_questions=plan_json.get("total", 0)
    )


@router.post("/next", response_model=InterviewNextResponse)
def next_interview_step(
    request: InterviewNextRequest,
    session: Session = Depends(get_session)
):
    """Process answer and get next question/followup."""
    interview_session = session.get(InterviewSession, request.session_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    if interview_session.ended_at:
        raise HTTPException(status_code=400, detail="Interview session already ended")
    
    # Get plan and current turn
    plan = json.loads(interview_session.plan_json or "{}")
    plan_items = plan.get("items", [])
    
    # Get current turn index
    turns = session.exec(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == request.session_id)
        .order_by(InterviewTurn.turn_index.desc())
    ).all()
    
    current_turn_index = len(turns)
    
    if current_turn_index > 0 and not request.is_followup:
        # Previous turn exists - this is the answer to the last question
        prev_turn = turns[0]
        question_id = prev_turn.question_id
        question = session.get(QuestionBank, question_id)
    else:
        # New question from plan
        if current_turn_index >= len(plan_items):
            # Interview done
            return InterviewNextResponse(
                interviewer_message="Thank you! The interview is complete.",
                followup_question=None,
                next_question=None,
                is_done=True,
                progress={"turn_index": current_turn_index, "total": len(plan_items)}
            )
        
        plan_item = plan_items[current_turn_index]
        question_id = plan_item.get("selected_question_id")
        question = session.get(QuestionBank, question_id)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Get role profile for scoring
    job_spec = session.get(JobSpec, interview_session.job_spec_id)
    role_profile = json.loads(job_spec.jd_profile_json) if job_spec and job_spec.jd_profile_json else {}
    
    # Score answer
    topics = json.loads(question.topics_json or "[]")
    reference_solution = question.solution_text if question.question_type.value == "code" else None
    
    score_json = score_answer(
        question.question_text,
        request.user_transcript,
        request.user_code,
        role_profile,
        reference_solution,
        topics
    )
    
    # Generate follow-up if needed
    followup = maybe_generate_followup(
        question.question_text,
        request.user_transcript,
        score_json,
        role_profile
    )
    
    followup_json = json.dumps({"text": followup}) if followup else None
    
    # Create turn record
    turn = InterviewTurn(
        id=str(uuid.uuid4()),
        session_id=request.session_id,
        turn_index=current_turn_index,
        question_id=question.id,
        question_snapshot=question.question_text,
        user_transcript=request.user_transcript,
        user_code=request.user_code,
        score_json=json.dumps(score_json),
        topics_json=json.dumps(topics),
        followup_json=followup_json
    )
    session.add(turn)
    session.commit()
    
    # Build response
    interviewer_message = "Thank you for your answer."
    if followup:
        interviewer_message += f" {followup}"
    
    # Check if interview is done
    is_done = current_turn_index + 1 >= len(plan_items)
    next_question_data = None
    
    if not is_done:
        # Get next question
        next_plan_item = plan_items[current_turn_index + 1]
        next_question_id = next_plan_item.get("selected_question_id")
        next_question = session.get(QuestionBank, next_question_id)
        
        if next_question:
            next_question_data = {
                "question_id": next_question.id,
                "text": next_question.question_text,
                "type": next_plan_item.get("type", "open"),
                "topics": json.loads(next_question.topics_json or "[]")
            }
    
    return InterviewNextResponse(
        interviewer_message=interviewer_message,
        followup_question={"text": followup} if followup else None,
        next_question=next_question_data,
        is_done=is_done,
        progress={"turn_index": current_turn_index + 1, "total": len(plan_items)}
    )


@router.post("/end", response_model=InterviewEndResponse)
def end_interview(
    request: InterviewEndRequest,
    session: Session = Depends(get_session)
):
    """End interview session."""
    interview_session = session.get(InterviewSession, request.session_id)
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    
    from datetime import datetime
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
