from backend.models import QuestionType
from tests.backend.fixtures.sample_data import create_question_bank


def test_interview_workflow(client, db_session):
    create_question_bank(
        db_session,
        question_type=QuestionType.OPEN,
        question_text="Describe a tough problem you solved.",
        question_id="open:workflow1",
        topics=["problem solving"],
    )

    user_resp = client.post("/api/users/ensure", json={})
    user_id = user_resp.json()["user_id"]

    jd_resp = client.post("/api/jd/ingest", json={"user_id": user_id, "jd_text": "Python backend role"})
    job_spec_id = jd_resp.json()["job_spec_id"]

    cv_resp = client.post("/api/cv/ingest", json={"user_id": user_id, "cv_text": "Python APIs"})
    cv_version_id = cv_resp.json()["cv_version_id"]

    start_resp = client.post(
        "/api/interview/start",
        json={
            "user_id": user_id,
            "job_spec_id": job_spec_id,
            "cv_version_id": cv_version_id,
            "mode": "direct",
            "settings": {"num_open": 1, "num_code": 0, "duration_minutes": 5},
        },
    )
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]

    next_resp = client.post(
        "/api/interview/next",
        json={"session_id": session_id, "user_transcript": "I solved X", "user_code": None},
    )
    assert next_resp.status_code == 200

    end_resp = client.post("/api/interview/end", json={"session_id": session_id})
    assert end_resp.status_code == 200

    session_resp = client.get(f"/api/interview/session/{session_id}")
    assert session_resp.status_code == 200
    assert session_resp.json()["id"] == session_id
