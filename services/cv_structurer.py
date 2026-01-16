"""CV structuring service using Gemini to extract structured information."""

from typing import Dict
from .gemini_client import call_gemini_json


def structure_cv(cv_text: str) -> Dict:
    """
    Extract structured information from raw CV text.
    
    Args:
        cv_text: Raw CV text extracted from PDF
        
    Returns:
        Structured CV data as dictionary with sections and evidence_map
    """
    prompt = f"""Extract structured information from this CV text. Return ONLY valid JSON with no markdown formatting.

CV Text:
{cv_text[:15000]}  # Limit to prevent token overflow

Return a JSON object with this exact structure:
{{
  "candidate_level": "junior|mid|senior|unknown",
  "sections": {{
    "summary": {{"text": "..."}},
    "experience": [
      {{
        "title": "...",
        "company": "...",
        "dates": "...",
        "bullets": ["..."],
        "skills": ["..."]
      }}
    ],
    "education": [
      {{
        "degree": "...",
        "school": "...",
        "dates": "...",
        "gpa": null
      }}
    ],
    "projects": [
      {{
        "name": "...",
        "bullets": ["..."],
        "skills": ["..."]
      }}
    ],
    "skills": {{
      "languages": [],
      "frameworks": [],
      "tools": [],
      "cloud": []
    }},
    "links": []
  }},
  "evidence_map": {{
    "python": [
      {{
        "quote": "...",
        "start": 123,
        "end": 145
      }}
    ]
  }}
}}

Requirements:
- candidate_level: Estimate based on years of experience, seniority indicators
- sections: Extract all relevant sections. Use empty arrays/objects if section is missing
- evidence_map: For each skill mentioned, include at least one entry with:
  - quote: A short excerpt (10-50 chars) showing where the skill appears
  - start: Approximate character offset in original text
  - end: Approximate end offset
- Keep evidence_map entries for major technical skills (languages, frameworks, tools)
- Be robust: handle missing sections gracefully"""

    try:
        result = call_gemini_json(prompt)
        
        # Validate and ensure all required keys exist
        if "candidate_level" not in result:
            result["candidate_level"] = "unknown"
        
        if "sections" not in result:
            result["sections"] = {}
        
        # Ensure sections structure
        required_sections = ["summary", "experience", "education", "projects", "skills", "links"]
        for section in required_sections:
            if section not in result["sections"]:
                if section == "summary":
                    result["sections"][section] = {"text": ""}
                elif section == "skills":
                    result["sections"][section] = {"languages": [], "frameworks": [], "tools": [], "cloud": []}
                else:
                    result["sections"][section] = []
        
        if "evidence_map" not in result:
            result["evidence_map"] = {}
        
        return result
        
    except Exception as e:
        # Return minimal structure on error
        return {
            "candidate_level": "unknown",
            "sections": {
                "summary": {"text": ""},
                "experience": [],
                "education": [],
                "projects": [],
                "skills": {"languages": [], "frameworks": [], "tools": [], "cloud": []},
                "links": []
            },
            "evidence_map": {}
        }
