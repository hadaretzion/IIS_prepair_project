"""Unified LLM client with Gemini primary and Groq fallback.

Set USE_GROQ_PRIMARY=true in .env to use Groq as the default LLM (avoids Gemini quota issues).
"""

import os
from typing import Optional
from backend.services.gemini_client import call_gemini, is_gemini_available
from backend.services.groq_client import call_groq, is_groq_available


def _get_default_preference() -> str:
    """Get default LLM preference from environment."""
    if os.environ.get("USE_GROQ_PRIMARY", "").lower() in ("true", "1", "yes"):
        return "groq"
    return "gemini"


def call_llm(system_prompt: str, user_prompt: str, prefer: Optional[str] = None) -> str:
    """Call an LLM with fallback strategy.
    
    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt for the LLM
        prefer: Which LLM to prefer ("gemini" or "groq"). If None, uses USE_GROQ_PRIMARY env var.
    
    Returns:
        LLM response text
    """
    prefer = (prefer or _get_default_preference()).lower()

    if prefer == "groq":
        if is_groq_available():
            return call_groq(system_prompt, user_prompt)
        if is_gemini_available():
            return call_gemini(system_prompt, user_prompt)
    else:
        if is_gemini_available():
            return call_gemini(system_prompt, user_prompt)
        if is_groq_available():
            return call_groq(system_prompt, user_prompt)

    raise ValueError("No LLM configured. Set GEMINI_API_KEY or GROQ_API_KEY.")
