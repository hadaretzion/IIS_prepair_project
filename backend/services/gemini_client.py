"""LLM client with safe fallbacks (Grok via xAI)."""

import json
import os
from pathlib import Path
from typing import Optional

import httpx


def get_gemini_api_key() -> Optional[str]:
    """Get Grok/XAI API key from environment variable or api_keys.json."""
    # Try environment variable first (prefer Grok/xAI keys)
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key
    
    # Try api_keys.json file
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        api_keys_path = project_root / "api_keys.json"
        
        if api_keys_path.exists():
            with open(api_keys_path, "r") as f:
                keys = json.load(f)
                api_key = (
                    keys.get("GROK_API_KEY")
                    or keys.get("XAI_API_KEY")
                    or keys.get("GEMINI_API_KEY")
                )
                if api_key:
                    return api_key
    except Exception:
        pass
    
    return None


def call_gemini(system_prompt: str, user_prompt: str, timeout: int = 30) -> str:
    """
    Call Grok (xAI) with system and user prompts.

    Returns:
        Response text as string

    Raises:
        ValueError: If API key is missing or call fails
    """
    api_key = get_gemini_api_key()
    if not api_key:
        raise ValueError("GROK_API_KEY not found in environment or api_keys.json")

    base_url = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
    model_name = os.getenv("GROK_MODEL", "grok-2-latest")

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if response.status_code >= 400:
            raise ValueError(f"Grok API error: {response.status_code} {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise ValueError(f"Grok API error: {str(e)}")
