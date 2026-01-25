from backend.models import QuestionType
from tests.backend.fixtures.sample_data import create_question_bank


def test_full_user_journey(client, db_session):
    create_question_bank(
        db_session,
        question_type=QuestionType.OPEN,
        question_text="Tell me about yourself.",
        question_id="open:full1",
        topics=["communication"],
    )

    user_resp = client.post("/api/users/ensure", json={})
    user_id = user_resp.json()["user_id"]

    jd_resp = client.post("/api/jd/ingest", json={"user_id": user_id, "jd_text": "Python backend role"})
    job_spec_id = jd_resp.json()["job_spec_id"]

    cv_resp = client.post("/api/cv/ingest", json={"user_id": user_id, "cv_text": "Python APIs"})
    cv_version_id = cv_resp.json()["cv_version_id"]

    analyze_resp = client.post(
        "/api/cv/analyze",
        json={"user_id": user_id, "cv_version_id": cv_version_id, "job_spec_id": job_spec_id},
    )
    assert analyze_resp.status_code == 200

    interview_resp = client.post(
        "/api/interview/start",
        json={
            "user_id": user_id,
            "job_spec_id": job_spec_id,
            "cv_version_id": cv_version_id,
            "mode": "after_cv",
            "settings": {"num_open": 1, "num_code": 0, "duration_minutes": 5},
        },
    )
    assert interview_resp.status_code == 200
    session_id = interview_resp.json()["session_id"]

    client.post(
        "/api/interview/next",
        json={"session_id": session_id, "user_transcript": "Answer", "user_code": None},
    )
    client.post("/api/interview/end", json={"session_id": session_id})

    progress_resp = client.get(f"/api/progress/overview?user_id={user_id}&job_spec_id={job_spec_id}")
    assert progress_resp.status_code == 200
