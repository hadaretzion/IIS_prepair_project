"""AI-powered CV analysis service using Gemini."""

import json
from typing import Dict, Any, List
from backend.services.gemini_client import call_gemini


def analyze_cv_with_ai(cv_text: str, jd_text: str, role_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze CV against job description using AI.
    
    Returns:
        {
            "match_score": float (0-1),
            "strengths": List[str],
            "gaps": List[str],
            "suggestions": List[str]
        }
    """
    system_prompt = """You are a senior technical recruiter and CV optimization expert with 15+ years of experience.
You understand ATS (Applicant Tracking Systems), hiring manager psychology, and what makes candidates stand out.
Analyze CVs with depth and provide genuinely useful, specific feedback that goes beyond surface-level observations.
Always respond with valid JSON only."""

    must_have = role_profile.get("must_have_topics", [])
    nice_to_have = role_profile.get("nice_to_have_topics", [])

    user_prompt = f"""Perform a deep analysis of this CV against the job description. Think like a hiring manager who sees hundreds of applications.

CV:
{cv_text[:4000]}

Job Description:
{jd_text[:2000]}

Required Skills: {', '.join(must_have[:10])}
Nice-to-have Skills: {', '.join(nice_to_have[:5])}

Return a JSON object with this structure:
{{
    "match_score": 0.75,
    "strengths": [
        "Your GNN project demonstrates exactly the kind of ML engineering the role requires - you should lead with this. The F1 score of 87.1% is a concrete achievement that proves competence.",
        "Python proficiency is evident through multiple academic projects - this satisfies the core technical requirement",
        "Cross-functional teamwork shown in the 3-person team project aligns with the collaborative culture mentioned in the JD"
    ],
    "gaps": [
        "No Docker/containerization experience mentioned (critical): The JD lists this as required. Even basic Docker knowledge would help - consider adding any exposure you have",
        "Missing cloud platform experience (AWS/GCP/Azure): Modern ML roles almost always involve cloud deployment. This gap may cause immediate rejection by ATS",
        "No production/deployment experience visible: Academic projects are valuable, but the JD hints at wanting someone who can ship code to real users"
    ],
    "suggestions": [
        "URGENT - Address Docker gap: Add a weekend project using Docker. Even 'Containerized Flask ML API using Docker for local development' shows initiative. The JD explicitly requires this.",
        "Quantify your GNN project impact more specifically: Instead of 'outperforming standard baselines', write 'Achieved 23% improvement over baseline LSTM model in defender position prediction, reducing prediction error from X to Y meters'. Numbers stick in recruiters' minds.",
        "Add a 'Technical Skills' section formatted for ATS: List skills in a single line like 'Python, TensorFlow, PyTorch, scikit-learn, pandas, Git' - ATS systems scan for exact keyword matches.",
        "Your 'Profile' section is too generic. Rewrite it to mirror JD language: 'Data Science student specializing in deep learning and computer vision, seeking to apply ML engineering skills in a fast-paced production environment' directly echoes what they're looking for."
    ]
}}

CRITICAL RULES:
- match_score: Calculate based on must-have coverage (70% weight) + nice-to-have (30% weight)
- strengths: 3-5 items. Each must reference SPECIFIC content from the CV and explain WHY it matters for THIS job. No generic statements like "Experience with Python".
- gaps: 3-5 items. Prioritize by severity. Explain the CONSEQUENCE of each gap (ATS rejection, interview weakness, etc.)
- suggestions: 3-5 items. Each suggestion must be:
  1. Specific to THIS CV (reference actual content to change)
  2. Actionable (tell them exactly what to write/add)
  3. Connected to the JD (explain which requirement it addresses)
  4. Include a concrete example or rewrite when possible
- AVOID generic advice like "add more keywords" or "quantify achievements" without specific examples
- Return ONLY valid JSON, no markdown formatting"""

    try:
        response_text = call_gemini(system_prompt, user_prompt)
        
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        return {
            "match_score": max(0.0, min(1.0, float(result.get("match_score", 0.5)))),
            "strengths": list(result.get("strengths", []))[:5],
            "gaps": list(result.get("gaps", []))[:5],
            "suggestions": list(result.get("suggestions", []))[:5]
        }
        
    except Exception as e:
        print(f"AI CV analysis failed: {e}")
        raise


def generate_cv_improvements(cv_text: str, jd_text: str, gaps: List[str]) -> Dict[str, Any]:
    """
    Generate specific CV improvement recommendations using AI.
    
    Returns:
        {
            "improved_sections": [
                {
                    "section": "Experience",
                    "original": "...",
                    "improved": "...",
                    "explanation": "..."
                }
            ],
            "new_content_suggestions": List[str],
            "formatting_tips": List[str]
        }
    """
    system_prompt = """You are an expert CV writer and career coach. Generate specific, actionable CV improvements.
Always respond with valid JSON only."""
    
    user_prompt = f"""Improve this CV for the target job:

Current CV:
{cv_text[:3500]}

Target Job:
{jd_text[:1500]}

Identified Gaps: {', '.join(gaps[:5])}

Return a JSON object with specific improvements:
{{
    "improved_sections": [
        {{
            "section": "Professional Summary",
            "original": "Experienced software developer...",
            "improved": "Results-driven software engineer with 5+ years...",
            "explanation": "Added specific metrics and aligned with job keywords"
        }}
    ],
    "new_content_suggestions": [
        "Add a 'Technical Skills' section highlighting Python, Docker, and AWS",
        "Include a project demonstrating API design experience"
    ],
    "formatting_tips": [
        "Use consistent bullet point formatting",
        "Quantify achievements where possible"
    ]
}}

Rules:
- Provide 2-4 section improvements with before/after examples
- Give 3-5 new content suggestions
- Include 2-3 formatting tips
- Be specific and actionable
- Return ONLY valid JSON"""

    try:
        response_text = call_gemini(system_prompt, user_prompt)
        
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response_text)
        
        return {
            "improved_sections": list(result.get("improved_sections", []))[:4],
            "new_content_suggestions": list(result.get("new_content_suggestions", []))[:5],
            "formatting_tips": list(result.get("formatting_tips", []))[:3]
        }
        
    except Exception as e:
        print(f"CV improvement generation failed: {e}")
        raise


def suggest_cv_rewrite(cv_text: str, jd_text: str, section: str = "summary") -> str:
    """
    Generate a rewritten version of a specific CV section.
    
    Args:
        cv_text: Full CV text
        jd_text: Target job description
        section: Section to rewrite (summary, experience, skills)
    
    Returns:
        Rewritten section text
    """
    system_prompt = """You are an expert CV writer. Rewrite CV sections to be more impactful and targeted."""
    
    user_prompt = f"""Rewrite the {section} section of this CV for the target job:

Current CV:
{cv_text[:3000]}

Target Job:
{jd_text[:1500]}

Focus on:
1. Using strong action verbs
2. Including relevant keywords from the job description
3. Quantifying achievements where possible
4. Being concise yet impactful

Return ONLY the rewritten {section} section text, no JSON or markdown formatting."""

    try:
        response_text = call_gemini(system_prompt, user_prompt)
        return response_text.strip()
    except Exception as e:
        print(f"CV section rewrite failed: {e}")
        raise
