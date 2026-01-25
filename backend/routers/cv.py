"""CV management router."""

import uuid
import json
import hashlib
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session
from backend.db import get_session
from backend.models import User, CVVersion, CVAnalysisResult, JobSpec
from backend.schemas import (
    CVIngestRequest, CVIngestResponse,
    CVAnalyzeRequest, CVAnalyzeResponse,
    CVSaveRequest, CVSaveResponse,
    CVImproveResponse, CVImprovements
)
from backend.services.role_profile import extract_role_profile
from backend.services.cv_analyzer import analyze_cv_with_ai, generate_cv_improvements

router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.post("/ingest", response_model=CVIngestResponse)
def ingest_cv(
    request: CVIngestRequest,
    session: Session = Depends(get_session)
):
    """Ingest CV text and create CV version."""
    # Ensure user exists
    user = session.get(User, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create CV version
    cv_version = CVVersion(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        cv_text=request.cv_text,
        source="manual"
    )
    session.add(cv_version)
    session.commit()
    session.refresh(cv_version)
    
    return CVIngestResponse(
        cv_version_id=cv_version.id,
        cv_profile_json=None  # Optional minimal profile
    )


@router.post("/ingest-pdf", response_model=CVIngestResponse)
async def ingest_cv_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session: Session = Depends(get_session)
):
    """Ingest CV from PDF file and create CV version."""
    # Ensure user exists
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read file contents
        contents = await file.read()
        pdf_file = io.BytesIO(contents)
        
        # Extract text from PDF
        from src.shared.pdf_extractor import extract_pdf_text
        cv_text = extract_pdf_text(pdf_file)
        
        # Create CV version using extracted text
        cv_version = CVVersion(
            id=str(uuid.uuid4()),
            user_id=user_id,
            cv_text=cv_text,
            source="pdf_upload"
        )
        session.add(cv_version)
        session.commit()
        session.refresh(cv_version)
        
        return CVIngestResponse(
            cv_version_id=cv_version.id,
            cv_profile_json=None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.post("/analyze", response_model=CVAnalyzeResponse)
def analyze_cv(
    request: CVAnalyzeRequest,
    session: Session = Depends(get_session)
):
    """Analyze CV against job spec."""
    cv_version = session.get(CVVersion, request.cv_version_id)
    if not cv_version:
        raise HTTPException(status_code=404, detail="CV version not found")
    
    job_spec = session.get(JobSpec, request.job_spec_id)
    if not job_spec:
        raise HTTPException(status_code=404, detail="Job spec not found")
    
    # Extract role profile if not exists
    if not job_spec.jd_profile_json:
        role_profile = extract_role_profile(cv_version.cv_text, job_spec.jd_text)
        job_spec.jd_profile_json = json.dumps(role_profile)
        session.add(job_spec)
        session.commit()
    else:
        role_profile = json.loads(job_spec.jd_profile_json)
    
    # Use AI-powered analysis for comprehensive feedback
    try:
        ai_analysis = analyze_cv_with_ai(cv_version.cv_text, job_spec.jd_text, role_profile)
        match_score = ai_analysis.get("match_score", 0.5)
        strengths = ai_analysis.get("strengths", [])
        gaps = ai_analysis.get("gaps", [])
        suggestions = ai_analysis.get("suggestions", [])
    except Exception as e:
        # Fallback to heuristic analysis
        match_score = _compute_match_score(cv_version.cv_text, role_profile)
        strengths = _extract_strengths(cv_version.cv_text, role_profile)
        gaps = _extract_gaps(cv_version.cv_text, role_profile)
        suggestions = _generate_suggestions(cv_version.cv_text, role_profile, gaps)
    
    focus = {
        "must_have_topics": role_profile.get("must_have_topics", []),
        "nice_to_have_topics": role_profile.get("nice_to_have_topics", [])
    }
    
    # Save analysis result
    analysis = CVAnalysisResult(
        id=str(uuid.uuid4()),
        cv_version_id=request.cv_version_id,
        job_spec_id=request.job_spec_id,
        user_id=request.user_id,
        match_score=match_score,
        strengths_json=json.dumps(strengths),
        gaps_json=json.dumps(gaps),
        suggestions_json=json.dumps(suggestions),
        focus_json=json.dumps(focus)
    )
    session.add(analysis)
    session.commit()
    
    # Compute readiness snapshot
    from backend.services.readiness import compute_readiness_snapshot
    compute_readiness_snapshot(session, request.user_id, request.job_spec_id, context="cv_analysis")
    
    return CVAnalyzeResponse(
        match_score=match_score,
        strengths=strengths,
        gaps=gaps,
        suggestions=suggestions,
        role_focus=focus,
        cv_text=cv_version.cv_text
    )


@router.post("/save", response_model=CVSaveResponse)
def save_cv(
    request: CVSaveRequest,
    session: Session = Depends(get_session)
):
    """Save improved CV version."""
    user = session.get(User, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    parent_version = None
    if request.parent_cv_version_id:
        parent_version = session.get(CVVersion, request.parent_cv_version_id)
    
    # Create new CV version
    cv_version = CVVersion(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        cv_text=request.updated_cv_text,
        source="improved",
        parent_cv_version_id=request.parent_cv_version_id
    )
    session.add(cv_version)
    session.commit()
    session.refresh(cv_version)
    
    return CVSaveResponse(new_cv_version_id=cv_version.id)


@router.post("/improve", response_model=CVImproveResponse)
def get_cv_improvements(
    request: CVAnalyzeRequest,
    session: Session = Depends(get_session)
):
    """Get AI-powered CV improvement suggestions."""
    cv_version = session.get(CVVersion, request.cv_version_id)
    if not cv_version:
        raise HTTPException(status_code=404, detail="CV version not found")
    
    job_spec = session.get(JobSpec, request.job_spec_id)
    if not job_spec:
        raise HTTPException(status_code=404, detail="Job spec not found")
    
    try:
        role_profile = json.loads(job_spec.jd_profile_json) if job_spec.jd_profile_json else {}
        
        gaps = _extract_gaps(cv_version.cv_text, role_profile)
        gap_topics = [g.replace("Missing: ", "") for g in gaps]
        
        improvements = generate_cv_improvements(
            cv_version.cv_text,
            job_spec.jd_text,
            gap_topics
        )
        
        return CVImproveResponse(
            success=True,
            improvements=CVImprovements(**improvements)
        )
    except Exception as e:
        return CVImproveResponse(
            success=False,
            improvements=CVImprovements(
                improved_sections=[],
                new_content_suggestions=[
                    "Highlight your most relevant experience for this role",
                    "Add quantifiable achievements to strengthen your CV",
                    "Include keywords from the job description"
                ],
                formatting_tips=[
                    "Use consistent formatting throughout",
                    "Keep bullet points concise and action-oriented"
                ]
            )
        )


def _compute_match_score(cv_text: str, role_profile: dict) -> float:
    """Compute match score with weighted importance."""
    must_have = role_profile.get("must_have_topics", [])
    nice_to_have = role_profile.get("nice_to_have_topics", [])
    cv_lower = cv_text.lower()

    # Must-have skills weighted at 70%, nice-to-have at 30%
    must_have_matches = sum(1 for topic in must_have if topic.lower() in cv_lower)
    nice_matches = sum(1 for topic in nice_to_have if topic.lower() in cv_lower)

    must_have_score = (must_have_matches / len(must_have)) if must_have else 0.5
    nice_score = (nice_matches / len(nice_to_have)) if nice_to_have else 0.5

    return min(1.0, must_have_score * 0.7 + nice_score * 0.3)


def _extract_strengths(cv_text: str, role_profile: dict) -> list:
    """Extract detailed strengths from CV with context."""
    must_have = role_profile.get("must_have_topics", [])
    nice_to_have = role_profile.get("nice_to_have_topics", [])
    cv_lower = cv_text.lower()

    strengths = []

    # Find matching must-have skills with context
    for topic in must_have:
        if topic.lower() in cv_lower:
            # Try to find contextual evidence
            if "project" in cv_lower and topic.lower() in cv_lower:
                strengths.append(f"Demonstrated {topic} skills through hands-on project work - directly aligns with a core job requirement")
            elif "experience" in cv_lower or "year" in cv_lower:
                strengths.append(f"Professional experience with {topic} - a must-have skill for this role")
            else:
                strengths.append(f"Background in {topic} matches key job requirement")

    # Add nice-to-have matches as bonus strengths
    for topic in nice_to_have[:2]:
        if topic.lower() in cv_lower:
            strengths.append(f"Additional expertise in {topic} - a valued bonus skill that sets you apart from other candidates")

    # Add general CV strengths based on content analysis
    if "gpa" in cv_lower or "honors" in cv_lower or "dean" in cv_lower:
        strengths.append("Strong academic performance signals dedication and learning ability")
    if "team" in cv_lower or "collaborat" in cv_lower or "led" in cv_lower:
        strengths.append("Evidence of teamwork and collaboration skills - essential for most roles")
    if any(metric in cv_lower for metric in ["%", "increased", "reduced", "improved", "achieved"]):
        strengths.append("Quantified achievements demonstrate impact-focused mindset")

    return strengths[:5]


def _extract_gaps(cv_text: str, role_profile: dict) -> list:
    """Extract detailed gaps with impact explanation."""
    must_have = role_profile.get("must_have_topics", [])
    nice_to_have = role_profile.get("nice_to_have_topics", [])
    cv_lower = cv_text.lower()

    gaps = []

    # Critical gaps (must-have skills missing)
    for topic in must_have:
        if topic.lower() not in cv_lower:
            gaps.append(f"Missing {topic} (critical): This is a core requirement. Without it, ATS systems may auto-reject your application")

    # Important gaps (nice-to-have skills that could strengthen application)
    nice_missing = [t for t in nice_to_have if t.lower() not in cv_lower]
    if nice_missing:
        gaps.append(f"Could strengthen with: {', '.join(nice_missing[:3])} - these bonus skills would increase your competitiveness")

    # Structural gaps
    if "github" not in cv_lower and "portfolio" not in cv_lower:
        gaps.append("No portfolio/GitHub link: Technical roles benefit greatly from visible code samples")
    if not any(metric in cv_lower for metric in ["%", "increased", "reduced", "saved", "achieved"]):
        gaps.append("Lack of quantified achievements: Numbers make your impact tangible and memorable")

    return gaps[:5]


def _generate_suggestions(cv_text: str, role_profile: dict, gaps: list) -> list:
    """Generate detailed, actionable improvement suggestions."""
    must_have = role_profile.get("must_have_topics", [])
    cv_lower = cv_text.lower()
    suggestions = []

    # Specific suggestions for missing must-have skills
    missing_critical = [t for t in must_have if t.lower() not in cv_lower]

    if missing_critical:
        topic = missing_critical[0]
        suggestions.append(
            f"Add '{topic}' to your Skills section even if experience is limited. "
            f"Then, in your Projects section, describe any coursework, personal project, or online certification "
            f"involving {topic}. Example: '{topic} - Completed hands-on project implementing X, gaining practical experience with Y and Z.'"
        )

    if len(missing_critical) > 1:
        topic = missing_critical[1]
        suggestions.append(
            f"Consider adding a 'Technical Learning' or 'Certifications' section to address the {topic} gap. "
            f"Free certifications from platforms like Coursera, LinkedIn Learning, or vendor-specific programs "
            f"(AWS, Google, Microsoft) can quickly demonstrate initiative and foundational knowledge."
        )

    # Suggestions for strengthening existing content
    if "project" in cv_lower:
        suggestions.append(
            "Strengthen your project descriptions using the STAR format: Situation (context/challenge), "
            "Task (your specific role), Action (technologies/methods used), Result (quantified impact). "
            "Example: 'Improved model accuracy by 15% by implementing feature engineering pipeline using pandas and scikit-learn.'"
        )

    # ATS optimization suggestions
    suggestions.append(
        "Mirror the exact terminology from the job description. If the JD says 'machine learning', "
        "use 'machine learning' not just 'ML'. ATS systems often do literal keyword matching, "
        "so using the exact phrases increases your match score."
    )

    # Professional summary suggestion
    if "summary" not in cv_lower and "objective" not in cv_lower and "profile" not in cv_lower:
        suggestions.append(
            "Add a 3-4 line Professional Summary at the top of your CV. This should highlight: "
            "(1) your current role/status, (2) your key technical strengths relevant to this job, "
            "and (3) what you're looking for. This helps recruiters quickly understand your fit."
        )

    return suggestions[:5]
