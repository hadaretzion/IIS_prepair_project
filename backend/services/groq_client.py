"""Groq client (OpenAI-compatible) for fallback LLM calls."""

import os
from typing import Optional
import httpx

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
# Updated from mixtral-8x7b-32768 (decommissioned) to llama-3.3-70b-versatile (recommended replacement)
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_groq_api_key() -> Optional[str]:
    """Return the GROQ API key if configured."""
    return GROQ_API_KEY


def is_groq_available() -> bool:
    """Check if Groq is configured."""
    return bool(GROQ_API_KEY)


def call_groq(system_prompt: str, user_prompt: str, model: Optional[str] = None, timeout: int = 30) -> str:
    """Call Groq (OpenAI-compatible) chat completions API."""
    if not GROQ_API_KEY:
        raise ValueError("Groq API not configured. Please set GROQ_API_KEY in .env file.")

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{GROQ_BASE_URL}/chat/completions"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise ValueError(f"Groq API error: {response.status_code} {response.text}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})
    return message.get("content", "") or ""
