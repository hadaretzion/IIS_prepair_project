"""Gemini 2.5 Pro client for JSON-structured API calls."""

import os
import json
import google.generativeai as genai
from typing import Dict, Optional


def get_gemini_api_key() -> str:
    """Get Gemini API key from environment variable."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not set. "
            "Please set it in Replit Secrets or your environment."
        )
    return api_key


def call_gemini_json(prompt: str, max_retries: int = 1) -> dict:
    """
    Call Gemini 2.5 Pro with a prompt and return structured JSON.
    
    Args:
        prompt: The prompt string (should include JSON format instructions)
        max_retries: Maximum number of retries if JSON parsing fails
        
    Returns:
        Parsed JSON as a dictionary
        
    Raises:
        ValueError: If API key is missing or response cannot be parsed as JSON
        Exception: For other API errors
    """
    api_key = get_gemini_api_key()
    genai.configure(api_key=api_key)
    
    # Configure model with JSON mode
    generation_config = {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }
    
    # Note: Using gemini-2.5-pro
    # To use a different model (e.g., gemini-1.5-flash), change the model_name here
    model = genai.GenerativeModel(
        model_name="gemini-2.5-pro",
        generation_config=generation_config
    )
    
    # Ensure prompt requests JSON
    json_prompt = prompt
    if "```json" not in prompt.lower() and "json" not in prompt.lower():
        json_prompt = f"{prompt}\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no code blocks, no explanations outside the JSON structure."
    
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = model.generate_content(json_prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            result = json.loads(response_text)
            return result
            
        except json.JSONDecodeError as e:
            last_error = f"Failed to parse JSON response (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
            if attempt < max_retries:
                continue
            raise ValueError(
                f"{last_error}\n\nResponse received: {response_text[:500]}"
            )
        except Exception as e:
            if "API key" in str(e) or "authentication" in str(e).lower():
                raise ValueError(f"Gemini API authentication failed: {str(e)}")
            raise Exception(f"Gemini API error: {str(e)}")
    
    raise ValueError(last_error or "Failed to get valid JSON response from Gemini")
