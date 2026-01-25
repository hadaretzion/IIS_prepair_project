import json

from backend.services.readiness import compute_readiness_snapshot
from backend.models import CVAnalysisResult, InterviewSession, InterviewTurn, InterviewMode
from tests.backend.fixtures.sample_data import create_cv_version, create_job_spec, create_user


def test_compute_readiness_snapshot(db_session):
    user = create_user(db_session, user_id="user-ready")
    job_spec = create_job_spec(db_session, job_spec_id="job-ready")
    cv_version = create_cv_version(db_session, user_id=user.id)

    analysis = CVAnalysisResult(
        cv_version_id=cv_version.id,
        job_spec_id=job_spec.id,
        user_id=user.id,
        match_score=0.7,
        strengths_json=json.dumps(["Python", "REST"]),
        gaps_json=json.dumps(["Docker"]),
        suggestions_json=json.dumps(["Add Docker experience"]),
        focus_json=json.dumps({"must_have_topics": ["Python"]}),
    )
    db_session.add(analysis)
    db_session.commit()

    session = InterviewSession(
        user_id=user.id,
        job_spec_id=job_spec.id,
        cv_version_id=cv_version.id,
        mode=InterviewMode.DIRECT,
        plan_json=json.dumps({"items": [{"selected_question_id": "open:1"}]}),
    )
    db_session.add(session)
    db_session.commit()

    turn = InterviewTurn(
        session_id=session.id,
        turn_index=0,
        question_id="open:1",
        question_snapshot="Tell me about yourself.",
        user_transcript="I have 5 years experience.",
        score_json=json.dumps({"overall": 0.8}),
        topics_json=json.dumps(["communication"]),
    )
    db_session.add(turn)
    db_session.commit()

    snapshot = compute_readiness_snapshot(db_session, user.id, job_spec.id, context="interview_end")
    assert snapshot.readiness_score > 0
    assert snapshot.cv_score >= 0
    assert snapshot.interview_score >= 0
