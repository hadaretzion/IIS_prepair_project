"""Scoring service for CV-JD matching."""

from typing import Dict, List, Set
import re
from collections import Counter


# Skill normalization synonyms
SKILL_SYNONYMS = {
    "javascript": ["js", "ecmascript", "node.js", "nodejs"],
    "python": ["py"],
    "react": ["reactjs", "react.js"],
    "aws": ["amazon web services", "amazon aws"],
    "kubernetes": ["k8s"],
    "docker": ["docker container"],
    "git": ["git version control"],
    "sql": ["mysql", "postgresql", "postgres", "sql server"],
    "java": ["java programming"],
    "typescript": ["ts"],
    "c++": ["cpp", "c plus plus"],
    "c#": ["csharp", "c sharp"],
}


def normalize_skill(skill: str) -> str:
    """
    Normalize skill name for matching.
    
    Args:
        skill: Raw skill string
        
    Returns:
        Normalized skill string
    """
    normalized = skill.lower().strip()
    
    # Check synonyms
    for key, synonyms in SKILL_SYNONYMS.items():
        if normalized in synonyms or normalized == key:
            return key
        for syn in synonyms:
            if syn in normalized or normalized in syn:
                return key
    
    return normalized


def extract_skills_from_cv(cv_data: Dict) -> Set[str]:
    """Extract all skills from CV structure."""
    skills = set()
    
    # From skills section
    skills_section = cv_data.get("sections", {}).get("skills", {})
    for category in ["languages", "frameworks", "tools", "cloud"]:
        for skill in skills_section.get(category, []):
            skills.add(normalize_skill(skill))
    
    # From experience
    for exp in cv_data.get("sections", {}).get("experience", []):
        for skill in exp.get("skills", []):
            skills.add(normalize_skill(skill))
    
    # From projects
    for proj in cv_data.get("sections", {}).get("projects", []):
        for skill in proj.get("skills", []):
            skills.add(normalize_skill(skill))
    
    return skills


def compute_keyword_overlap(text1: str, text2: str) -> float:
    """
    Compute simple keyword overlap score between two texts.
    
    Returns:
        Float between 0 and 1 representing overlap
    """
    # Simple tokenization and word counting
    words1 = set(re.findall(r'\b\w+\b', text1.lower()))
    words2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def compute_responsibilities_score(cv_text: str, responsibilities: List[str]) -> float:
    """Compute how well CV covers job responsibilities."""
    if not responsibilities:
        return 1.0
    
    cv_lower = cv_text.lower()
    scores = []
    for resp in responsibilities:
        # Check if responsibility keywords appear in CV
        resp_words = set(re.findall(r'\b\w+\b', resp.lower()))
        # Filter out common stop words
        resp_words = {w for w in resp_words if len(w) > 3}
        if not resp_words:
            continue
        
        matches = sum(1 for word in resp_words if word in cv_lower)
        score = matches / len(resp_words) if resp_words else 0
        scores.append(score)
    
    return sum(scores) / len(scores) if scores else 0.0


def compute_seniority_alignment(cv_level: str, jd_level: str) -> float:
    """Compute seniority alignment score."""
    levels = ["junior", "mid", "senior"]
    
    cv_idx = levels.index(cv_level) if cv_level in levels else -1
    jd_idx = levels.index(jd_level) if jd_level in levels else -1
    
    if cv_idx == -1 or jd_idx == -1:
        return 0.5  # Unknown gets neutral score
    
    diff = abs(cv_idx - jd_idx)
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.5
    else:
        return 0.0


def compute_match_score(cv_data: Dict, jd_data: Dict, cv_text: str) -> Dict:
    """
    Compute comprehensive match score between CV and JD.
    
    Args:
        cv_data: Structured CV data
        jd_data: Structured JD data
        cv_text: Raw CV text for keyword matching
        
    Returns:
        Analysis dictionary with match score, strengths, gaps, etc.
    """
    # Extract and normalize skills
    cv_skills = extract_skills_from_cv(cv_data)
    required_skills = {normalize_skill(s) for s in jd_data.get("required_skills", [])}
    preferred_skills = {normalize_skill(s) for s in jd_data.get("preferred_skills", [])}
    
    # Compute hit rates
    required_hit_rate = 0.0
    if required_skills:
        covered_required = cv_skills.intersection(required_skills)
        required_hit_rate = len(covered_required) / len(required_skills)
    
    preferred_hit_rate = 0.0
    if preferred_skills:
        covered_preferred = cv_skills.intersection(preferred_skills)
        preferred_hit_rate = len(covered_preferred) / len(preferred_skills)
    
    # Compute responsibilities score
    responsibilities_score = compute_responsibilities_score(
        cv_text, jd_data.get("responsibilities", [])
    )
    
    # Compute seniority alignment
    cv_level = cv_data.get("candidate_level", "unknown")
    jd_level = jd_data.get("seniority", "unknown")
    seniority_alignment = compute_seniority_alignment(cv_level, jd_level)
    
    # Weighted score calculation
    score = 100 * (
        0.55 * required_hit_rate +
        0.15 * preferred_hit_rate +
        0.20 * responsibilities_score +
        0.10 * seniority_alignment
    )
    score = max(0, min(100, round(score)))
    
    # Determine label
    if score >= 85:
        label = "excellent fit"
    elif score >= 70:
        label = "mostly fit"
    elif score >= 50:
        label = "partial fit"
    else:
        label = "weak fit"
    
    # Identify strengths and gaps
    covered_required = list(cv_skills.intersection(required_skills))
    missing_required = list(required_skills - cv_skills)
    missing_preferred = list(preferred_skills - cv_skills)
    
    strengths = []
    if covered_required:
        strengths.append(f"Covered {len(covered_required)}/{len(required_skills)} required skills")
    if preferred_hit_rate > 0.5:
        strengths.append("Strong match with preferred skills")
    if seniority_alignment >= 0.5:
        strengths.append("Good seniority alignment")
    if not strengths:
        strengths.append("Some relevant experience present")
    
    gaps = []
    if missing_required:
        gaps.append(f"Missing {len(missing_required)} required skills: {', '.join(missing_required[:5])}")
    if missing_preferred:
        gaps.append(f"Missing {len(missing_preferred)} preferred skills")
    if seniority_alignment < 0.5:
        gaps.append(f"Seniority mismatch: CV ({cv_level}) vs JD ({jd_level})")
    if not gaps:
        gaps.append("Minor gaps in skill alignment")
    
    # Soft skill focus
    soft_skill_focus = jd_data.get("soft_skills", [])[:3]
    
    # Simulation plan
    if missing_required:
        simulation_plan = f"Focus on highlighting {missing_required[0]} and related experience"
    elif missing_preferred:
        simulation_plan = f"Emphasize experience with {missing_preferred[0]}"
    else:
        simulation_plan = "Refine existing content to better align with job responsibilities"
    
    return {
        "match": {
            "score": score,
            "label": label,
            "breakdown": {
                "required_skills_score": round(required_hit_rate * 100, 1),
                "preferred_skills_score": round(preferred_hit_rate * 100, 1),
                "responsibilities_score": round(responsibilities_score * 100, 1),
                "seniority_alignment": round(seniority_alignment * 100, 1)
            }
        },
        "soft_skill_focus": soft_skill_focus,
        "strengths": strengths,
        "gaps": gaps,
        "simulation_plan": simulation_plan,
        "covered_required": covered_required,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred
    }
