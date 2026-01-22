"""Gemini AI client using Replit AI Integrations."""

import os
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Replit AI Integrations - provides Gemini access without requiring your own API key
AI_INTEGRATIONS_GEMINI_API_KEY = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
AI_INTEGRATIONS_GEMINI_BASE_URL = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")

# Initialize Gemini client with Replit AI Integrations
client = genai.Client(
    api_key=AI_INTEGRATIONS_GEMINI_API_KEY,
    http_options={
        'api_version': '',
        'base_url': AI_INTEGRATIONS_GEMINI_BASE_URL   
    }
)


def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg 
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower() 
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, 'status') and exception.status == 429)
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def call_gemini(system_prompt: str, user_prompt: str, timeout: int = 30) -> str:
    """
    Call Gemini with system and user prompts using Replit AI Integrations.

    Args:
        system_prompt: System instructions for the model
        user_prompt: User's prompt/question
        timeout: Not used with new SDK, kept for compatibility

    Returns:
        Response text as string

    Raises:
        ValueError: If API call fails
    """
    if not AI_INTEGRATIONS_GEMINI_BASE_URL or not AI_INTEGRATIONS_GEMINI_API_KEY:
        raise ValueError("Gemini AI Integrations not configured. Please set up the integration.")
    
    try:
        # Combine system prompt with user prompt for better results
        full_prompt = f"{system_prompt}\n\nUser Request:\n{user_prompt}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=8192,
                temperature=0.3,
            )
        )
        
        return response.text or ""
        
    except Exception as e:
        error_msg = str(e)
        if "FREE_CLOUD_BUDGET_EXCEEDED" in error_msg:
            raise ValueError("Cloud budget exceeded. Please check your Replit credits.")
        raise ValueError(f"Gemini API error: {error_msg}")


def generate_text(prompt: str) -> str:
    """Simple text generation with Gemini."""
    if not AI_INTEGRATIONS_GEMINI_BASE_URL or not AI_INTEGRATIONS_GEMINI_API_KEY:
        raise ValueError("Gemini AI Integrations not configured.")
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text or ""
    except Exception as e:
        raise ValueError(f"Gemini API error: {str(e)}")


def is_gemini_available() -> bool:
    """Check if Gemini AI is available and configured."""
    return bool(AI_INTEGRATIONS_GEMINI_BASE_URL and AI_INTEGRATIONS_GEMINI_API_KEY)
