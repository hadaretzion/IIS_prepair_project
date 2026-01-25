"""Question selection and interview plan building."""

import json
import random
from typing import Dict, Any, List, Optional, Set
from sqlmodel import Session, select
from backend.models import (
    QuestionBank, QuestionHistory, InterviewSession, InterviewTurn, JobSpec, QuestionType
)
from datetime import datetime, timedelta


def build_interview_plan(
    user_id: str,
    job_spec_id: str,
    cv_version_id: Optional[str],
    mode: str,
    settings: Dict[str, Any],
    session: Session
) -> Dict[str, Any]:
    """
    Build interview plan with weighted sampling and diversity constraints.
    
    Args:
        session: Database session (must be provided by caller)
    
    Returns:
        {
            "total": int,
            "sections": [{"name": str, "count": int}, ...],
            "items": [
                {
                    "slot": int,
                    "type": "open"|"code",
                    "candidates": [...],
                    "selected_question_id": str
                },
                ...
            ],
            "created_from": {...}
        }
    """
    num_open = settings.get("num_open", 4)
    num_code = settings.get("num_code", 2)
    duration_minutes = settings.get("duration_minutes", 12)
    strict_mode = settings.get("strict_mode", "realistic")
    
    # Get job spec and role profile
    job_spec = session.get(JobSpec, job_spec_id)
    if not job_spec:
        raise ValueError(f"Job spec {job_spec_id} not found")
    
    role_profile = json.loads(job_spec.jd_profile_json) if job_spec.jd_profile_json else {}
    topic_weights = role_profile.get("weights", {})
    
    # Get recent question IDs to exclude (last 3 sessions or last X days)
    recent_question_ids = _get_recent_question_ids(session, user_id, job_spec_id, max_days=7, max_sessions=3)
    
    # Build plan items
    items = []
    slot = 0
    
    # Section 1: Open questions
    open_questions = _select_questions(
        session, QuestionType.OPEN, num_open, topic_weights, 
        recent_question_ids, user_id, job_spec_id
    )
    
    for q in open_questions:
        topics = json.loads(q.topics_json or "[]")
        items.append({
            "slot": slot,
            "type": "open",
            "candidates": [{
                "question_id": q.id,
                "difficulty": None,
                "topics": topics,
                "score": _compute_match_score(topics, topic_weights)
            }],
            "selected_question_id": q.id
        })
        slot += 1
    
    # Section 2: Code questions (with adaptive candidates)
    code_questions = _select_questions(
        session, QuestionType.CODE, num_code * 3, topic_weights,
        recent_question_ids, user_id, job_spec_id
    )
    
    # Group by difficulty
    by_difficulty = {"Easy": [], "Medium": [], "Hard": []}
    for q in code_questions:
        diff = q.difficulty or "Medium"
        by_difficulty.get(diff, by_difficulty["Medium"]).append(q)
    
    # Assign candidates per slot (2-3 per slot, sorted easier->harder)
    for slot_idx in range(num_code):
        candidates = []
        for difficulty in ["Easy", "Medium", "Hard"]:
            if by_difficulty[difficulty] and len(candidates) < 2:
                q = by_difficulty[difficulty].pop(0)
                topics = json.loads(q.topics_json or "[]")
                candidates.append({
                    "question_id": q.id,
                    "difficulty": difficulty,
                    "topics": topics,
                    "score": _compute_match_score(topics, topic_weights)
                })
        
        if candidates:
            # Sort easier -> harder
            candidates.sort(key=lambda c: {"Easy": 1, "Medium": 2, "Hard": 3}.get(c["difficulty"], 2))
            selected = candidates[0]  # Start with easiest
            
            items.append({
                "slot": slot,
                "type": "code",
                "candidates": candidates,
                "selected_question_id": selected["question_id"]
            })
            slot += 1
    
    return {
        "total": len(items),
        "sections": [
            {"name": "behavioral", "count": num_open},
            {"name": "technical", "count": num_code}
        ],
        "items": items,
        "created_from": {
            "role_profile": role_profile,
            "constraints": {
                "excluded_recent": len(recent_question_ids),
                "strict_mode": strict_mode
            }
        }
    }


def _get_recent_question_ids(
    session: Session,
    user_id: str,
    job_spec_id: str,
    max_days: int = 7,
    max_sessions: int = 3
) -> Set[str]:
    """Get question IDs asked recently for this user+job_spec."""
    cutoff_date = datetime.utcnow() - timedelta(days=max_days)
    
    # Get recent sessions
    recent_sessions = session.exec(
        select(InterviewSession.id)
        .where(InterviewSession.user_id == user_id)
        .where(InterviewSession.job_spec_id == job_spec_id)
        .where(InterviewSession.created_at >= cutoff_date)
        .order_by(InterviewSession.created_at.desc())
        .limit(max_sessions)
    ).all()
    
    if not recent_sessions:
        return set()
    
    # Get question IDs from these sessions
    question_ids = session.exec(
        select(InterviewTurn.question_id)
        .where(InterviewTurn.session_id.in_(recent_sessions))
        .where(InterviewTurn.question_id.isnot(None))
    ).all()
    
    return set(qid for qid in question_ids if qid)


def _compute_match_score(topics: List[str], topic_weights: Dict[str, float]) -> float:
    """Compute match score based on topic intersection with role profile weights."""
    if not topics or not topic_weights:
        return 0.5  # Default score
    
    score = 0.0
    matches = 0
    
    for topic in topics:
        topic_lower = topic.lower()
        # Exact match
        if topic_lower in topic_weights:
            score += topic_weights[topic_lower]
            matches += 1
        else:
            # Partial match
            for weight_topic, weight in topic_weights.items():
                if topic_lower in weight_topic or weight_topic in topic_lower:
                    score += weight * 0.5  # Partial match gets half weight
                    matches += 1
                    break
    
    return score / max(1, len(topics))  # Normalize


def _select_questions(
    session: Session,
    question_type: QuestionType,
    num_questions: int,
    topic_weights: Dict[str, float],
    exclude_ids: Set[str],
    user_id: str,
    job_spec_id: str
) -> List[QuestionBank]:
    """Select questions with weighted sampling and diversity."""
    # Get candidates
    query = select(QuestionBank).where(QuestionBank.question_type == question_type)
    candidates = list(session.exec(query).all())
    
    # Filter excluded
    candidates = [q for q in candidates if q.id not in exclude_ids]
    
    if not candidates:
        return []
    
    # Score candidates
    scored = []
    for q in candidates:
        topics = json.loads(q.topics_json or "[]")
        score = _compute_match_score(topics, topic_weights)
        scored.append((q, score))
    
    # Sort by score
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Weighted sampling with diversity
    selected = []
    used_ids = set()
    selected_topics_sets = []
    
    # Take top candidates with diversity check
    top_k = min(num_questions * 3, len(scored))
    candidates_pool = scored[:top_k]
    
    while len(selected) < num_questions and candidates_pool:
        remaining = [(q, s) for q, s in candidates_pool if q.id not in used_ids]
        
        if not remaining:
            break
        
        # Weighted selection (favor higher scores)
        weights = [s ** 2 for _, s in remaining]
        if sum(weights) <= 0:
            chosen_q, chosen_score = random.choice(remaining)
        else:
            chosen_q, chosen_score = random.choices(remaining, weights=weights, k=1)[0]
        
        # Check diversity (Jaccard similarity with selected)
        chosen_topics = set(json.loads(chosen_q.topics_json or "[]"))
        
        max_overlap = 0.0
        for prev_topics in selected_topics_sets:
            intersection = len(chosen_topics & prev_topics)
            union = len(chosen_topics | prev_topics)
            overlap = intersection / union if union > 0 else 0.0
            max_overlap = max(max_overlap, overlap)
        
        # If overlap too high and we have alternatives, skip
        if max_overlap > 0.7 and len(remaining) > 1:
            candidates_pool.remove((chosen_q, chosen_score))
            continue
        
        selected.append(chosen_q)
        used_ids.add(chosen_q.id)
        selected_topics_sets.append(chosen_topics)
    
    return selected[:num_questions]
