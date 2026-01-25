"""Job Description (JD) management router."""

import json
import hashlib
import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session
from backend.db import get_session
from backend.models import JobSpec
from backend.schemas import JDIngestRequest, JDIngestResponse, JDGetResponse
from backend.services.role_profile import extract_role_profile

router = APIRouter(prefix="/api/jd", tags=["jd"])


@router.post("/ingest", response_model=JDIngestResponse)
def ingest_jd(
    request: JDIngestRequest,
    session: Session = Depends(get_session)
):
    """Ingest JD text and create/return job spec."""
    # Compute JD hash
    jd_hash = hashlib.md5(request.jd_text.encode()).hexdigest()
    
    # Check if job spec already exists
    from sqlmodel import select
    existing = session.exec(
        select(JobSpec).where(JobSpec.jd_hash == jd_hash)
    ).first()
    
    if existing:
        # Return existing
        profile = json.loads(existing.jd_profile_json) if existing.jd_profile_json else None
        return JDIngestResponse(
            job_spec_id=existing.id,
            jd_hash=existing.jd_hash,
            jd_profile_json=profile
        )
    
    # Extract role profile (without CV for now)
    try:
        role_profile = extract_role_profile("", request.jd_text)
        profile_json = json.dumps(role_profile)
    except Exception as e:
        print(f"⚠️  Role profile extraction failed: {e}")
        # Fallback
        role_profile = {
            "role_title": "Software Developer",
            "seniority": "mid",
            "must_have_topics": [],
            "nice_to_have_topics": [],
            "soft_skills": [],
            "coding_focus": [],
            "weights": {}
        }
        profile_json = json.dumps(role_profile)
    
    # Create job spec
    job_spec = JobSpec(
        id=str(uuid.uuid4()),
        jd_hash=jd_hash,
        jd_text=request.jd_text,
        jd_profile_json=profile_json
    )
    session.add(job_spec)
    session.commit()
    session.refresh(job_spec)
    
    return JDIngestResponse(
        job_spec_id=job_spec.id,
        jd_hash=job_spec.jd_hash,
        jd_profile_json=role_profile
    )


@router.post("/ingest-pdf", response_model=JDIngestResponse)
async def ingest_jd_pdf(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session: Session = Depends(get_session)
):
    """Ingest JD from PDF file and create/return job spec."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read file contents
        contents = await file.read()
        pdf_file = io.BytesIO(contents)
        
        # Extract text from PDF
        from src.shared.pdf_extractor import extract_pdf_text
        jd_text = extract_pdf_text(pdf_file)
        
        # Use existing ingest logic
        # Compute JD hash
        jd_hash = hashlib.md5(jd_text.encode()).hexdigest()
        
        # Check if job spec already exists
        from sqlmodel import select
        existing = session.exec(
            select(JobSpec).where(JobSpec.jd_hash == jd_hash)
        ).first()
        
        if existing:
            # Return existing
            profile = json.loads(existing.jd_profile_json) if existing.jd_profile_json else None
            return JDIngestResponse(
                job_spec_id=existing.id,
                jd_hash=existing.jd_hash,
                jd_profile_json=profile
            )
        
        # Extract role profile
        try:
            role_profile = extract_role_profile("", jd_text)
            profile_json = json.dumps(role_profile)
        except Exception as e:
            print(f"⚠️  Role profile extraction failed: {e}")
            # Fallback
            role_profile = {
                "role_title": "Software Developer",
                "seniority": "mid",
                "must_have_topics": [],
                "nice_to_have_topics": [],
                "soft_skills": [],
                "coding_focus": [],
                "weights": {}
            }
            profile_json = json.dumps(role_profile)
        
        # Create job spec
        job_spec = JobSpec(
            id=str(uuid.uuid4()),
            jd_hash=jd_hash,
            jd_text=jd_text,
            jd_profile_json=profile_json
        )
        session.add(job_spec)
        session.commit()
        session.refresh(job_spec)
        
        return JDIngestResponse(
            job_spec_id=job_spec.id,
            jd_hash=job_spec.jd_hash,
            jd_profile_json=role_profile
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.get("/{job_spec_id}", response_model=JDGetResponse)
def get_jd(
    job_spec_id: str,
    session: Session = Depends(get_session)
):
    """Get job spec by ID."""
    job_spec = session.get(JobSpec, job_spec_id)
    if not job_spec:
        raise HTTPException(status_code=404, detail="Job spec not found")
    
    profile = json.loads(job_spec.jd_profile_json) if job_spec.jd_profile_json else None
    
    return JDGetResponse(
        id=job_spec.id,
        jd_hash=job_spec.jd_hash,
        jd_text=job_spec.jd_text,
        created_at=job_spec.created_at,
        jd_profile_json=profile
    )
