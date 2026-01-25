from backend.models import InterviewSession, QuestionType
from tests.backend.fixtures.sample_data import (
    create_cv_version,
    create_job_spec,
    create_question_bank,
    create_user,
)


def test_interview_start_next_end(client, db_session):
    user = create_user(db_session, user_id="user-int")
    job_spec = create_job_spec(db_session, job_spec_id="job-int")
    cv_version = create_cv_version(db_session, user_id=user.id)
    create_question_bank(
        db_session,
        question_type=QuestionType.OPEN,
        question_text="Tell me about yourself.",
        question_id="open:1",
        topics=["communication"],
    )

    start_response = client.post(
        "/api/interview/start",
        json={
            "user_id": user.id,
            "job_spec_id": job_spec.id,
            "cv_version_id": cv_version.id,
            "mode": "after_cv",
            "settings": {"num_open": 1, "num_code": 0, "duration_minutes": 5},
        },
    )
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["session_id"]
    assert start_data["first_question"]["text"]

    next_response = client.post(
        "/api/interview/next",
        json={
            "session_id": start_data["session_id"],
            "user_transcript": "I am a backend engineer.",
            "user_code": None,
            "is_followup": False,
            "elapsed_seconds": 0,
        },
    )
    assert next_response.status_code == 200
    next_data = next_response.json()
    assert next_data["is_done"] is True

    end_response = client.post(
        "/api/interview/end",
        json={"session_id": start_data["session_id"]},
    )
    assert end_response.status_code == 200
    assert end_response.json()["ok"] is True

    session = db_session.get(InterviewSession, start_data["session_id"])
    assert session is not None
    assert session.ended_at is not None
