"""Conversation strategy and state management for interview flow."""

import json
from typing import Dict, Any, Optional
from backend.services.llm_client import call_llm
from backend.services.agent_guardrails import filter_question


def determine_conversation_strategy(score_dict: Dict[str, Any], word_count: int, previous_answers: int = 0) -> Dict[str, Any]:
    """
    Determine if/how to follow up based on score and answer characteristics.
    
    Args:
        score_dict: Output from score_answer()
        word_count: Number of words in the answer
        previous_answers: Number of previous answers to this question (for context)
    
    Returns:
        {
            "should_followup": bool,
            "followup_type": "clarify" | "probe_deeper" | "challenge" | None,
            "satisfaction_level": float,  # 0-1, how satisfied are we with this answer
            "followup_urgency": int  # 0=can skip, 1=should ask, 2=must ask
        }
    """
    overall = score_dict.get("overall", 0)
    rubric = score_dict.get("rubric", {})
    depth = rubric.get("depth", 0)
    clarity = rubric.get("clarity", 0)
    
    # Excellent answer - move on
    if overall >= 0.75 and word_count > 60:
        return {
            "should_followup": False,
            "followup_type": None,
            "satisfaction_level": overall,
            "followup_urgency": 0
        }
    
    # Weak answer - must probe
    if overall < 0.5:
        followup_type = "probe_deeper" if depth < 0.5 else "clarify"
        if clarity < 0.4:
            followup_type = "clarify"
        
        return {
            "should_followup": True,
            "followup_type": followup_type,
            "satisfaction_level": overall,
            "followup_urgency": 2
        }
    
    # Too brief - ask for more detail
    if word_count < 50:
        return {
            "should_followup": True,
            "followup_type": "clarify",
            "satisfaction_level": overall,
            "followup_urgency": 1
        }
    
    # Borderline answer - conditional follow-up
    if overall < 0.65:
        followup_type = "probe_deeper" if depth < 0.6 else None
        return {
            "should_followup": followup_type is not None,
            "followup_type": followup_type,
            "satisfaction_level": overall,
            "followup_urgency": 1
        }
    
    # Good answer but could be deeper
    if depth < 0.65:
        return {
            "should_followup": True,
            "followup_type": "probe_deeper",
            "satisfaction_level": overall,
            "followup_urgency": 1
        }
    
    # Good answer - no follow-up needed
    return {
        "should_followup": False,
        "followup_type": None,
        "satisfaction_level": overall,
        "followup_urgency": 0
    }


def generate_contextual_followup(
    question: str,
    transcript: str,
    followup_type: str,
    score_dict: Dict[str, Any],
    previous_followups: list = None,
    role_profile: Dict[str, Any] = None
) -> Optional[str]:
    """
    Generate targeted follow-up based on type and context.
    
    Args:
        question: Original question
        transcript: User's answer
        followup_type: "clarify" | "probe_deeper" | "challenge"
        score_dict: Scoring result
        previous_followups: List of previous follow-up questions (to avoid repetition)
        role_profile: Job spec role profile (for context)
    
    Returns:
        Follow-up question string or None
    """
    if not followup_type:
        return None
    
    previous_followups = previous_followups or []
    
    try:
        system_prompt = """Generate natural, targeted follow-up questions for interview answers.
Always respond with valid JSON only."""
        
        followup_instructions = {
            "clarify": "Ask for clarification or a specific example to better understand the answer.",
            "probe_deeper": "Ask a deeper question that explores the reasoning, impact, or lessons learned.",
            "challenge": "Gently challenge or probe for more thorough thinking."
        }
        
        instruction = followup_instructions.get(followup_type, "Ask a relevant follow-up question.")
        
        previous_context = ""
        if previous_followups:
            previous_context = f"\nPrevious follow-ups (avoid repetition):\n" + "\n".join(f"- {fu}" for fu in previous_followups[-2:])
        
        user_prompt = f"""Generate a brief, natural follow-up question for this interview answer.

Original Question: {question}

Candidate's Answer: {transcript}

Feedback: {', '.join(score_dict.get('notes', [])[:2])}
Score: {score_dict.get('overall', 0):.2f}

Follow-up Type: {followup_type}
Instruction: {instruction}
{previous_context}

Return JSON with EXACTLY this structure:
{{
    "followup": "Can you give me a concrete example of when you applied this?"
}}

Return ONLY valid JSON."""
        
        response_text = call_llm(system_prompt, user_prompt)
        
        # Clean response
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        followup = result.get("followup")
        
        if followup and isinstance(followup, str) and len(followup.strip()) > 0:
            return filter_question(followup.strip())
        
        return None
        
    except Exception as e:
        print(f"⚠️  Contextual follow-up generation failed: {e}")
        return None


def should_continue_conversation(followup_count: int, satisfaction_level: float, max_followups: int = 3) -> bool:
    """
    Determine if we should ask another follow-up or move to next question.
    
    Rules:
    - Max 3 follow-ups per question
    - Exit early if satisfaction >= 0.7 after 1+ follow-up
    - Always exit if max_followups reached
    """
    if followup_count >= max_followups:
        return False  # Absolute max reached
    
    if satisfaction_level >= 0.7 and followup_count >= 1:
        return False  # Good enough after at least 1 follow-up
    
    return True
