"""Answer analysis agent for identifying gaps and follow-up strategy."""

import json
from typing import Dict, Any
from backend.services.llm_client import call_llm


def analyze_answer(question: str, answer: str, role_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the answer for gaps and strengths."""
    word_count = len((answer or "").split())

    system_prompt = """You are an expert interviewer. Return concise JSON only."""

    user_prompt = f"""Analyze this interview answer.

Question: {question}
Answer: {answer}
Role Profile: {json.dumps(role_profile or {}, ensure_ascii=False)}

Return JSON exactly like:
{{
  "score": 0.0,
  "strengths": ["..."],
  "gaps": ["..."],
  "followup_type": "clarify" | "probe_deeper" | "challenge" | null,
  "notes": ["short bullet"]
}}
"""

    try:
        response = call_llm(system_prompt, user_prompt)
        response = response.strip()
        if "```" in response:
            response = response.split("```", 1)[1].split("```", 1)[0].strip()
        data = json.loads(response)
        return {
            "score": float(data.get("score", 0.0)),
            "strengths": data.get("strengths", []) or [],
            "gaps": data.get("gaps", []) or [],
            "followup_type": data.get("followup_type"),
            "notes": data.get("notes", []) or [],
        }
    except Exception:
        # Heuristic fallback
        if word_count < 40:
            followup_type = "clarify"
            score = 0.45
        elif word_count < 80:
            followup_type = "probe_deeper"
            score = 0.6
        else:
            followup_type = None
            score = 0.75

        return {
            "score": score,
            "strengths": ["Communicated a relevant response"],
            "gaps": ["Add more detail or concrete examples"] if followup_type else [],
            "followup_type": followup_type,
            "notes": ["Heuristic analysis (LLM unavailable)"],
        }
