"""Scoring and follow-up generation for interview answers."""

import json
from typing import Dict, Any, Optional
from backend.services.gemini_client import call_gemini


def score_answer(
    question: str,
    user_transcript: str,
    user_code: Optional[str],
    role_profile: Dict[str, Any],
    reference_solution: Optional[str],
    topics: list
) -> Dict[str, Any]:
    """
    Score an answer using heuristics + optional Gemini scoring.
    
    Returns:
        {
            "overall": float (0-1),
            "rubric": {
                "clarity": float,
                "relevance": float,
                "structure": float,
                "correctness": float,
                "depth": float
            },
            "notes": List[str]
        }
    """
    # MVP: Use Gemini if available, otherwise heuristics
    try:
        system_prompt = """You are an expert interview evaluator. Score answers objectively and provide structured feedback.
Always respond with valid JSON only."""
        
        code_section = f'Code provided:\n{user_code[:1000]}' if user_code else ''
        ref_solution_section = f'Reference Solution:\n{reference_solution[:500]}' if reference_solution else ''
        
        user_prompt = f"""Evaluate this interview answer:

Question: {question}

Answer (transcript): {user_transcript}

{code_section}

Relevant Topics: {', '.join(topics[:10])}

{ref_solution_section}

Return a JSON object with this exact structure:
{{
    "overall": 0.75,
    "rubric": {{
        "clarity": 0.8,
        "relevance": 0.7,
        "structure": 0.8,
        "correctness": 0.7,
        "depth": 0.75
    }},
    "notes": ["Clear explanation", "Mentioned edge cases"]
}}

Rules:
- All scores are floats between 0.0 and 1.0
- For code questions, do NOT execute code. Score reasoning, approach, complexity mention, edge-cases.
- Use reference_solution only to evaluate approach, not to run code.
- notes should be short strings (max 3-4 items)
- Return ONLY valid JSON"""
        
        response_text = call_gemini(system_prompt, user_prompt)
        
        # Clean response
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        # Validate and normalize
        overall = float(result.get("overall", 0.5))
        overall = max(0.0, min(1.0, overall))
        
        rubric = result.get("rubric", {})
        normalized_rubric = {
            "clarity": max(0.0, min(1.0, float(rubric.get("clarity", 0.5)))),
            "relevance": max(0.0, min(1.0, float(rubric.get("relevance", 0.5)))),
            "structure": max(0.0, min(1.0, float(rubric.get("structure", 0.5)))),
            "correctness": max(0.0, min(1.0, float(rubric.get("correctness", 0.5)))),
            "depth": max(0.0, min(1.0, float(rubric.get("depth", 0.5)))),
        }
        
        notes = list(result.get("notes", []))[:4]
        
        return {
            "overall": overall,
            "rubric": normalized_rubric,
            "notes": notes
        }
        
    except Exception as e:
        print(f"⚠️  Gemini scoring failed: {e}. Using fallback heuristics.")
        return _fallback_scoring(question, user_transcript, user_code)


def _fallback_scoring(question: str, transcript: str, code: Optional[str]) -> Dict[str, Any]:
    """Fallback heuristic scoring."""
    # Simple heuristics
    words = len(transcript.split())
    base_score = min(0.8, max(0.4, words / 100.0))
    
    # Boost for code
    if code and len(code) > 20:
        base_score = min(1.0, base_score + 0.2)
    
    return {
        "overall": base_score,
        "rubric": {
            "clarity": base_score,
            "relevance": base_score,
            "structure": base_score,
            "correctness": base_score,
            "depth": base_score * 0.9
        },
        "notes": ["Heuristic scoring used"]
    }


def maybe_generate_followup(
    question: str,
    transcript: str,
    score_json: Dict[str, Any],
    role_profile: Dict[str, Any]
) -> Optional[str]:
    """
    Generate follow-up question if appropriate (score < 0.5 or too short).
    
    Returns:
        Follow-up question string or None
    """
    overall = score_json.get("overall", 0.5)
    word_count = len(transcript.split())
    
    # Only generate if score is low or answer too short
    if overall >= 0.5 and word_count > 50:
        return None
    
    try:
        system_prompt = """Generate concise follow-up questions for interview answers.
Always respond with valid JSON only."""
        
        user_prompt = f"""Based on this interview exchange, generate a brief follow-up question (one sentence).

Original Question: {question}
Answer: {transcript}
Score: {overall:.2f}
Weaknesses: {', '.join(score_json.get('notes', [])[:2])}

Return JSON:
{{
    "followup": "Can you provide a specific example of when you used this approach?"
}}

Or if no follow-up is needed:
{{
    "followup": null
}}

Return ONLY valid JSON."""
        
        response_text = call_gemini(system_prompt, user_prompt)
        
        # Clean response
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        followup = result.get("followup")
        
        if followup and isinstance(followup, str) and len(followup.strip()) > 0:
            return followup.strip()
        
        return None
        
    except Exception as e:
        print(f"⚠️  Follow-up generation failed: {e}")
        return None
