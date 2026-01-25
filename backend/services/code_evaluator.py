"""Code evaluation agent for assessing technical answers."""

import json
from typing import Dict, Any, Optional
from backend.services.llm_client import call_llm


def evaluate_code(question: str, code: Optional[str], reference_solution: Optional[str], role_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate code quality without executing it."""
    if not code:
        return {
            "score": None,
            "strengths": [],
            "issues": [],
            "complexity": None,
            "followup_type": None,
        }

    system_prompt = """You are a senior engineer reviewing code. Return concise JSON only."""
    user_prompt = f"""Review the candidate code.

Question: {question}
Code:
{code}

Reference (if any): {reference_solution or ""}
Role Profile: {json.dumps(role_profile or {}, ensure_ascii=False)}

Return JSON:
{{
  "score": 0.0,
  "strengths": ["..."],
  "issues": ["..."],
  "complexity": "low" | "medium" | "high" | null,
  "followup_type": "clarify" | "probe_deeper" | "challenge" | null
}}
"""

    try:
        response = call_llm(system_prompt, user_prompt, prefer="groq")
        response = response.strip()
        if "```" in response:
            response = response.split("```", 1)[1].split("```", 1)[0].strip()
        data = json.loads(response)
        return {
            "score": data.get("score"),
            "strengths": data.get("strengths", []) or [],
            "issues": data.get("issues", []) or [],
            "complexity": data.get("complexity"),
            "followup_type": data.get("followup_type"),
        }
    except Exception:
        return {
            "score": 0.55,
            "strengths": ["Code appears to attempt a solution"],
            "issues": ["Could not fully evaluate (LLM unavailable)"],
            "complexity": None,
            "followup_type": "clarify",
        }
