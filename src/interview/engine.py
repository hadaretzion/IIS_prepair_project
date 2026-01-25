"""Interview engine runtime logic."""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlmodel import Session, select
from src.models.database import InterviewSession, InterviewTurn, QuestionBank, UserSkillState, QuestionHistory, JobSpec
from src.interview.gemini_helpers import score_answer, maybe_generate_followup

ACKNOWLEDGEMENTS = [
    "Got it - let's keep going.",
    "Understood. Let's move to the next topic.",
    "Noted. Here's the next question.",
    "Alright, let's continue.",
]


def acknowledgement_for_turn(turn_number: int) -> str:
    """Return a varied acknowledgement so the interviewer feels natural."""
    if not ACKNOWLEDGEMENTS:
        return "Let's keep going."
    return ACKNOWLEDGEMENTS[turn_number % len(ACKNOWLEDGEMENTS)]
def get_next_question(
    session: Session,
    interview_session: InterviewSession,
    current_turn_number: int,
    last_score: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """Get the next question based on progress and performance."""
    
    plan = json.loads(interview_session.plan or "[]")
    
    if current_turn_number >= len(plan):
        return None  # Interview complete
    
    plan_item = plan[current_turn_number]
    
    # If this is a code question with candidates, adapt based on last score
    if plan_item.get("question_type") == "code" and plan_item.get("candidates"):
        candidates = plan_item["candidates"]
        
        if last_score is not None and len(candidates) > 1:
            # Adaptive selection: choose easier if score < 60, harder if > 85
            if last_score < 60:
                # Select easier candidate
                candidates.sort(key=lambda c: {"Easy": 1, "Medium": 2, "Hard": 3}.get(c.get("difficulty", "Medium"), 2))
            elif last_score > 85:
                # Select harder candidate
                candidates.sort(key=lambda c: {"Easy": 3, "Medium": 2, "Hard": 1}.get(c.get("difficulty", "Medium"), 2))
        
        # Use first candidate (sorted if adaptation occurred)
        selected = candidates[0]
        plan_item["question_id"] = selected["question_id"]
        plan_item["question_text"] = selected["question_text"]
        plan_item["difficulty"] = selected.get("difficulty")
    
    # Get question from database
    question = session.get(QuestionBank, plan_item["question_id"])
    if not question:
        return None
    
    return {
        "question_id": question.id,
        "question_text": question.question_text,
        "question_type": plan_item["question_type"],
        "topics": plan_item.get("topics", []),
        "difficulty": plan_item.get("difficulty"),
        "solution": question.solution if plan_item["question_type"] == "code" else None,
        "solution_url": question.solution_url if plan_item["question_type"] == "code" else None,
    }


def process_answer(
    session: Session,
    interview_session: InterviewSession,
    turn_number: int,
    user_transcript: str,
    user_code: Optional[str] = None,
    client_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process a user answer and return interviewer response and next question."""
    
    # Get current question from plan
    plan = json.loads(interview_session.plan or "[]")
    if turn_number >= len(plan):
        return {
            "interviewer_message": "Thank you! The interview is complete.",
            "next_question": None,
            "is_done": True,
            "progress": {"current": turn_number, "total": len(plan)},
        }
    
    plan_item = plan[turn_number]
    question = session.get(QuestionBank, plan_item["question_id"])
    
    if not question:
        return {
            "interviewer_message": "Let's move on to the next question.",
            "next_question": None,
            "is_done": True,
            "progress": {"current": turn_number, "total": len(plan)},
        }
    
    # Score the answer
    topics = plan_item.get("topics", [])
    reference_solution = question.solution if plan_item["question_type"] == "code" else None
    
    score_json = score_answer(
        question.question_text,
        user_transcript,
        reference_solution,
        topics
    )
    
    # Maybe generate follow-up
    followup = maybe_generate_followup(question.question_text, user_transcript, score_json)
    
    # Create turn record
    turn = InterviewTurn(
        session_id=interview_session.id,
        question_id=question.id,
        question_text=question.question_text,
        user_transcript=user_transcript,
        user_code=user_code,
        interviewer_message=acknowledgement_for_turn(turn_number),
        followup_question=followup,
        score_json=json.dumps(score_json),
        turn_number=turn_number,
        client_metrics=json.dumps(client_metrics) if client_metrics else None,
    )
    session.add(turn)
    
    # Update user skill state (for adaptive questioning)
    update_skill_state(session, interview_session.user_id, topics, score_json)
    
    # Record question history
    job_spec = session.get(JobSpec, interview_session.job_spec_id)
    if job_spec:
        history = QuestionHistory(
            user_id=interview_session.user_id,
            jd_hash=job_spec.jd_hash,
            question_id=question.id,
            session_id=interview_session.id,
        )
        session.add(history)
    
    session.commit()
    
    # Build response
    acknowledgement = acknowledgement_for_turn(turn_number)
    interviewer_message = acknowledgement
    if followup:
        interviewer_message = f"{acknowledgement} {followup}"
    
    # Get next question
    next_question_data = None
    is_done = False
    
    if turn_number + 1 < len(plan):
        next_question_data = get_next_question(
            session, interview_session, turn_number + 1, score_json.get("overall_score")
        )
    else:
        is_done = True
        interview_session.status = "completed"
        interview_session.ended_at = datetime.utcnow()
        session.commit()
    
    return {
        "interviewer_message": interviewer_message,
        "next_question": next_question_data,
        "is_done": is_done,
        "progress": {
            "current": turn_number + 1,
            "total": len(plan)
        },
        "score": score_json.get("overall_score"),
    }


def update_skill_state(
    session: Session,
    user_id: int,
    topics: List[str],
    score_json: Dict[str, Any]
):
    """Update user skill state based on answer scores."""
    skill_state = session.exec(
        select(UserSkillState).where(UserSkillState.user_id == user_id)
    ).first()
    
    topic_scores = score_json.get("topic_scores", {})
    overall_score = score_json.get("overall_score", 50)
    
    if not skill_state:
        skill_scores = {}
    else:
        skill_scores = json.loads(skill_state.skill_scores or "{}")
    
    # Update scores for topics
    for topic in topics:
        topic_key = topic.lower()
        if topic_key in topic_scores:
            new_score = topic_scores[topic_key]
        else:
            new_score = overall_score
        
        # Running average
        if topic_key in skill_scores:
            skill_scores[topic_key] = (skill_scores[topic_key] * 0.7 + new_score * 0.3)
        else:
            skill_scores[topic_key] = new_score
    
    if skill_state:
        skill_state.skill_scores = json.dumps(skill_scores)
        skill_state.updated_at = datetime.utcnow()
    else:
        skill_state = UserSkillState(
            user_id=user_id,
            skill_scores=json.dumps(skill_scores)
        )
        session.add(skill_state)
    
    session.commit()
