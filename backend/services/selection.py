"""Question selection and interview plan building."""

import json
import random
import re
from typing import Dict, Any, List, Optional, Set
from sqlmodel import Session, select
from backend.models import (
    QuestionBank, QuestionHistory, InterviewSession, InterviewTurn, JobSpec, QuestionType
)
from datetime import datetime, timedelta


SENSITIVE_PHRASES = (
    "leave your current company",
    "leave your current job",
    "why do you want to leave your current company",
    "why do you want to leave your current job",
)


UNSAFE_KEYWORD_PATTERN = re.compile(
    r"\b("
    r"age|married|marital|pregnan\w*|children|kids|family planning|religion|religious|"
    r"citizenship|nationality|ethnicity|race|racial|sexual orientation|gender identity|gender|"
    r"political affiliation|disability|medical condition|health condition|birth\s?date"
    r")\b",
    re.IGNORECASE,
)


def _is_question_allowed(question_text: str) -> bool:
    """Filter out boundary-crossing or inappropriate interview questions."""
    text = question_text or ""
    normalized = text.lower()
    if any(phrase in normalized for phrase in SENSITIVE_PHRASES):
        return False
    if UNSAFE_KEYWORD_PATTERN.search(text):
        return False
    return True


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
    # Handle both dict and Pydantic model for settings
    if hasattr(settings, 'num_open'):
        # Pydantic model
        num_open = settings.num_open if settings.num_open is not None else 4
        num_code = settings.num_code if settings.num_code is not None else 2
        duration_minutes = settings.duration_minutes if settings.duration_minutes is not None else 12
        strict_mode = getattr(settings, 'strict_mode', 'realistic') or 'realistic'
        question_style = getattr(settings, 'question_style', 50) or 50  # 0=technical, 100=personal
    else:
        # Dict (legacy support)
        num_open = settings.get("num_open", 4)
        num_code = settings.get("num_code", 2)
        duration_minutes = settings.get("duration_minutes", 12)
        strict_mode = settings.get("strict_mode", "realistic")
        question_style = settings.get("question_style", 50)
    
    # Get job spec and role profile
    job_spec = session.get(JobSpec, job_spec_id)
    if not job_spec:
        raise ValueError(f"Job spec {job_spec_id} not found")
    
    role_profile = json.loads(job_spec.jd_profile_json) if job_spec.jd_profile_json else {}
    topic_weights = role_profile.get("weights", {})
    
    # Get recent question IDs to exclude (last 3 sessions or last X days)
    recent_question_ids = _get_recent_question_ids(session, user_id, job_spec_id, max_days=7, max_sessions=3)
    
    # Build style weights based on question_style slider (0=technical, 100=personal)
    # These will be used to adjust question selection scoring
    style_weights = _compute_style_weights(question_style)
    
    # Build plan items
    items = []
    slot = 0
    
    # Section 1: Open questions
    open_questions = _select_questions(
        session, QuestionType.OPEN, num_open, topic_weights, 
        recent_question_ids, user_id, job_spec_id, style_weights
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
        recent_question_ids, user_id, job_spec_id, style_weights
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


# Topic categories for question style filtering
TECHNICAL_TOPICS = {
    'algorithms', 'data structures', 'system design', 'coding', 'architecture',
    'databases', 'api', 'performance', 'scalability', 'testing', 'debugging',
    'security', 'networking', 'distributed systems', 'concurrency', 'optimization',
    'design patterns', 'oop', 'functional programming', 'sql', 'nosql', 'cache',
    'microservices', 'rest', 'graphql', 'devops', 'ci/cd', 'cloud', 'aws', 'azure',
    'docker', 'kubernetes', 'linux', 'git', 'python', 'javascript', 'java', 'c++',
    'react', 'node', 'machine learning', 'ai', 'data science'
}

PERSONAL_TOPICS = {
    'teamwork', 'leadership', 'communication', 'motivation', 'career', 'goals',
    'conflict', 'collaboration', 'management', 'mentorship', 'culture', 'values',
    'work-life', 'growth', 'learning', 'feedback', 'challenges', 'achievements',
    'strengths', 'weaknesses', 'failure', 'success', 'stress', 'pressure',
    'decision making', 'problem solving', 'creativity', 'innovation', 'initiative',
    'adaptability', 'flexibility', 'priorities', 'time management', 'organization',
    'remote work', 'travel', 'relocation', 'salary', 'benefits', 'passion'
}


def _compute_style_weights(question_style: int) -> Dict[str, float]:
    """
    Compute topic style weights based on the question_style slider.
    
    Args:
        question_style: 0 = technical, 100 = personal
    
    Returns:
        Dict with 'technical_boost' and 'personal_boost' multipliers
    """
    # Normalize to 0-1 range
    style_ratio = question_style / 100.0
    
    # Calculate boosts (1.0 = neutral, >1 = boost, <1 = penalize)
    # At 0: technical gets 2.0 boost, personal gets 0.3
    # At 50: both get 1.0 (neutral)
    # At 100: technical gets 0.3, personal gets 2.0
    technical_boost = 2.0 - (1.7 * style_ratio)  # 2.0 -> 0.3
    personal_boost = 0.3 + (1.7 * style_ratio)   # 0.3 -> 2.0
    
    return {
        'technical_boost': technical_boost,
        'personal_boost': personal_boost
    }


def _get_topic_style_score(topics: List[str], style_weights: Dict[str, float]) -> float:
    """
    Calculate a style adjustment score for a question based on its topics.
    
    Returns a multiplier to adjust the base match score.
    """
    if not topics:
        return 1.0  # Neutral
    
    technical_count = 0
    personal_count = 0
    
    for topic in topics:
        topic_lower = topic.lower()
        # Check technical match
        for tech_topic in TECHNICAL_TOPICS:
            if tech_topic in topic_lower or topic_lower in tech_topic:
                technical_count += 1
                break
        # Check personal match
        for pers_topic in PERSONAL_TOPICS:
            if pers_topic in topic_lower or topic_lower in pers_topic:
                personal_count += 1
                break
    
    # Calculate weighted score
    total = len(topics)
    if total == 0:
        return 1.0
    
    tech_ratio = technical_count / total
    pers_ratio = personal_count / total
    
    # Apply style weights
    multiplier = 1.0 + (tech_ratio * (style_weights['technical_boost'] - 1.0)) + \
                 (pers_ratio * (style_weights['personal_boost'] - 1.0))
    
    return max(0.1, multiplier)  # Floor at 0.1 to never fully exclude


def _select_questions(
    session: Session,
    question_type: QuestionType,
    num_questions: int,
    topic_weights: Dict[str, float],
    exclude_ids: Set[str],
    user_id: str,
    job_spec_id: str,
    style_weights: Optional[Dict[str, float]] = None
) -> List[QuestionBank]:
    """Select questions with weighted sampling, diversity, and style preference."""
    # Default style weights if not provided
    if style_weights is None:
        style_weights = {'technical_boost': 1.0, 'personal_boost': 1.0}
    
    # Get candidates
    query = select(QuestionBank).where(QuestionBank.question_type == question_type)
    candidates = list(session.exec(query).all())
    
    # Filter excluded and boundary-crossing questions
    candidates = [
        q for q in candidates
        if q.id not in exclude_ids and _is_question_allowed(q.question_text)
    ]
    
    if not candidates:
        return []
    
    # Score candidates (combine role match score with style preference)
    scored = []
    for q in candidates:
        topics = json.loads(q.topics_json or "[]")
        base_score = _compute_match_score(topics, topic_weights)
        style_multiplier = _get_topic_style_score(topics, style_weights)
        final_score = base_score * style_multiplier
        scored.append((q, final_score))
    
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
