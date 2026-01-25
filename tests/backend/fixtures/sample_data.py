import hashlib
import json
import uuid

from backend.models import CVVersion, JobSpec, QuestionBank, QuestionType, User


def create_user(session, user_id: str | None = None) -> User:
    user = User(id=user_id or str(uuid.uuid4()))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_job_spec(
    session,
    jd_text: str = "Software Engineer role working with Python and APIs.",
    jd_profile: dict | None = None,
    job_spec_id: str | None = None,
) -> JobSpec:
    profile = jd_profile or {
        "role_title": "Software Engineer",
        "seniority": "mid",
        "must_have_topics": ["python", "rest"],
        "nice_to_have_topics": ["docker"],
        "soft_skills": ["communication"],
        "coding_focus": ["backend"],
        "weights": {"python": 0.9, "rest": 0.7, "docker": 0.4},
    }
    jd_hash = hashlib.md5(jd_text.encode()).hexdigest()
    job_spec = JobSpec(
        id=job_spec_id or str(uuid.uuid4()),
        jd_hash=jd_hash,
        jd_text=jd_text,
        jd_profile_json=json.dumps(profile),
    )
    session.add(job_spec)
    session.commit()
    session.refresh(job_spec)
    return job_spec


def create_cv_version(
    session,
    user_id: str,
    cv_text: str = "Experienced Python engineer with API design background.",
) -> CVVersion:
    cv_version = CVVersion(
        id=str(uuid.uuid4()),
        user_id=user_id,
        cv_text=cv_text,
        source="manual",
    )
    session.add(cv_version)
    session.commit()
    session.refresh(cv_version)
    return cv_version


def create_question_bank(
    session,
    question_type: QuestionType,
    question_text: str,
    question_id: str | None = None,
    topics: list[str] | None = None,
    difficulty: str | None = None,
) -> QuestionBank:
    qb = QuestionBank(
        id=question_id or f"{question_type.value}:{uuid.uuid4().hex[:8]}",
        question_type=question_type,
        question_text=question_text,
        topics_json=json.dumps(topics or ["python"]),
        difficulty=difficulty,
        source="test",
    )
    session.add(qb)
    session.commit()
    session.refresh(qb)
    return qb
