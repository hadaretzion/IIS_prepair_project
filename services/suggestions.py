"""Suggestions engine for CV improvements."""

from typing import Dict, List, Tuple
import re
from .gemini_client import call_gemini_json


def locate_anchor_span(cv_text: str, anchor_hint: str) -> Tuple[int, int]:
    """
    Locate approximate span in CV text based on anchor hint.
    
    Args:
        cv_text: Full CV text
        anchor_hint: Short substring to search for
        
    Returns:
        Tuple of (start, end) character offsets, or (0, 0) if not found
    """
    anchor_lower = anchor_hint.lower().strip()
    cv_lower = cv_text.lower()
    
    # Try exact match first
    idx = cv_lower.find(anchor_lower)
    if idx != -1:
        return (idx, idx + len(anchor_hint))
    
    # Try word-based fuzzy match
    anchor_words = anchor_hint.lower().split()[:3]  # Take first few words
    if len(anchor_words) >= 2:
        # Try to find the words close together
        for i in range(len(cv_text) - 50):
            snippet = cv_text[i:i+100].lower()
            if all(word in snippet for word in anchor_words):
                return (i, i + 100)
    
    return (0, 0)


def generate_suggestions(cv_text: str, cv_data: Dict, jd_data: Dict, current_score: int) -> List[Dict]:
    """
    Generate improvement suggestions using Gemini.
    
    Args:
        cv_text: Current CV text
        cv_data: Structured CV data
        jd_data: Structured JD data
        current_score: Current match score
        
    Returns:
        List of suggestion dictionaries
    """
    # Prepare context for suggestions
    missing_required = jd_data.get("missing_required", [])
    missing_preferred = jd_data.get("missing_preferred", [])
    missing_info = ""
    if missing_required or missing_preferred:
        missing_info = f"\n\nMissing Skills:\n- Required: {', '.join(missing_required[:10])}\n- Preferred: {', '.join(missing_preferred[:10])}"
    
    prompt = f"""Generate 6-10 actionable suggestions to improve this CV for better match with the job description.

Current CV Match Score: {current_score}/100

Job Requirements:
- Role: {jd_data.get('role_title', 'N/A')}
- Required Skills: {', '.join(jd_data.get('required_skills', [])[:10])}
- Preferred Skills: {', '.join(jd_data.get('preferred_skills', [])[:10])}
- Seniority: {jd_data.get('seniority', 'unknown')}{missing_info}

CV Text (first 5000 chars):
{cv_text[:5000]}

CRITICAL RULES:
1. DO NOT invent experience, skills, degrees, companies, or achievements that are not in the CV
2. Suggestions should only involve rewriting, reordering, clarifying, or deleting existing content
3. For suggestions that would require adding something not in the CV, set needs_user_confirmation=true
4. If needs_user_confirmation=true, do NOT include expected_delta until user confirms
5. Focus on better highlighting existing skills/experience that match job requirements
6. Keep suggestions specific and actionable

Return ONLY valid JSON array with this exact structure:
[
  {{
    "id": "SUG-01",
    "type": "rewrite|reorder|delete|clarify|add_optional",
    "title": "Brief title",
    "anchor_hint": "short substring from CV text to locate (15-30 chars)",
    "before": "Current text excerpt (if applicable)",
    "after": "Suggested replacement (if applicable)",
    "rationale": "Why this improves the match (1-2 sentences)",
    "expected_delta": 0-12,
    "risk": "low|medium|high",
    "needs_user_confirmation": false,
    "confirmation_prompt": null
  }}
]

Guidelines:
- type "rewrite": Improve wording/emphasis of existing content
- type "reorder": Move content to better position
- type "delete": Remove redundant/irrelevant content
- type "clarify": Make vague statements more specific
- type "add_optional": Add content if user has it (requires confirmation)
- expected_delta: Estimated score increase (0-12 points) ONLY if confirmed or no confirmation needed
- anchor_hint: Must be a real substring from the CV text provided above"""

    try:
        result = call_gemini_json(prompt)
        
        # Ensure result is a list
        if not isinstance(result, list):
            # Try to extract list from dict if wrapped
            if isinstance(result, dict) and "suggestions" in result:
                result = result["suggestions"]
            else:
                return []
        
        # Validate and clean suggestions
        validated_suggestions = []
        for i, sug in enumerate(result[:10]):  # Limit to 10
            # Ensure all required fields
            validated = {
                "id": sug.get("id", f"SUG-{i+1:02d}"),
                "type": sug.get("type", "rewrite"),
                "title": sug.get("title", "Improvement suggestion"),
                "anchor_hint": sug.get("anchor_hint", ""),
                "before": sug.get("before", ""),
                "after": sug.get("after", ""),
                "rationale": sug.get("rationale", ""),
                "expected_delta": min(12, max(0, sug.get("expected_delta", 0))),
                "risk": sug.get("risk", "low"),
                "needs_user_confirmation": sug.get("needs_user_confirmation", False),
                "confirmation_prompt": sug.get("confirmation_prompt")
            }
            
            # If needs confirmation, set expected_delta to 0 initially
            if validated["needs_user_confirmation"] and not validated.get("confirmed", False):
                validated["expected_delta"] = 0
            
            validated_suggestions.append(validated)
        
        return validated_suggestions
        
    except Exception as e:
        # Return empty list on error
        return []


def apply_suggestion(cv_text: str, suggestion: Dict) -> str:
    """
    Apply a suggestion to CV text.
    
    Args:
        cv_text: Current CV text
        suggestion: Suggestion dictionary with before/after
        
    Returns:
        Updated CV text
    """
    suggestion_type = suggestion.get("type", "rewrite")
    before = suggestion.get("before", "").strip()
    after = suggestion.get("after", "").strip()
    anchor_hint = suggestion.get("anchor_hint", "").strip()
    
    if not before and not anchor_hint:
        return cv_text  # No change if no anchor
    
    # Try to replace based on "before" text
    if before and before in cv_text:
        # Replace first occurrence
        cv_text = cv_text.replace(before, after, 1)
        return cv_text
    
    # Fallback: use anchor hint to locate and replace
    if anchor_hint:
        start, end = locate_anchor_span(cv_text, anchor_hint)
        if start < end:
            # Replace the span
            cv_text = cv_text[:start] + after + cv_text[end:]
            return cv_text
    
    # If nothing found, try case-insensitive match
    if before:
        import re
        pattern = re.escape(before)
        if re.search(pattern, cv_text, re.IGNORECASE):
            cv_text = re.sub(pattern, after, cv_text, count=1, flags=re.IGNORECASE)
            return cv_text
    
    return cv_text  # No change applied
