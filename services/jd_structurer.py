"""Job Description structuring service using Gemini to extract structured information."""

from typing import Dict
from .gemini_client import call_gemini_json


def structure_jd(jd_text: str) -> Dict:
    """
    Extract structured information from job description text.
    
    Args:
        jd_text: Raw job description text
        
    Returns:
        Structured JD data as dictionary
    """
    prompt = f"""Extract structured information from this job description. Return ONLY valid JSON with no markdown formatting.

Job Description:
{jd_text[:8000]}  # Limit to prevent token overflow

Return a JSON object with this exact structure:
{{
  "role_title": "...",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill3", "skill4"],
  "responsibilities": ["responsibility1", "responsibility2"],
  "soft_skills": ["communication", "teamwork"],
  "seniority": "junior|mid|senior|unknown"
}}

Requirements:
- role_title: The job title/role name
- required_skills: Skills explicitly marked as required or must-have
- preferred_skills: Skills marked as preferred, nice-to-have, or bonus
- responsibilities: Key responsibilities and duties (3-8 items)
- soft_skills: Soft skills mentioned (communication, leadership, etc.)
- seniority: Estimate level (junior = entry-level, mid = 2-5 years, senior = 5+ years)
- Use empty arrays if a category is not found"""

    try:
        result = call_gemini_json(prompt)
        
        # Validate and ensure all required keys exist
        required_keys = ["role_title", "required_skills", "preferred_skills", 
                        "responsibilities", "soft_skills", "seniority"]
        for key in required_keys:
            if key not in result:
                if key in ["required_skills", "preferred_skills", "responsibilities", "soft_skills"]:
                    result[key] = []
                elif key == "role_title":
                    result[key] = ""
                else:
                    result[key] = "unknown"
        
        return result
        
    except Exception as e:
        # Return minimal structure on error
        return {
            "role_title": "",
            "required_skills": [],
            "preferred_skills": [],
            "responsibilities": [],
            "soft_skills": [],
            "seniority": "unknown"
        }
