import json


def test_cv_workflow_end_to_end(client, monkeypatch):
    def fake_role_profile(_cv_text, _jd_text):
        return {
            "role_title": "Backend Engineer",
            "seniority": "mid",
            "must_have_topics": ["python"],
            "nice_to_have_topics": [],
            "soft_skills": [],
            "coding_focus": [],
            "weights": {"python": 0.9},
        }

    monkeypatch.setattr("backend.routers.jd.extract_role_profile", fake_role_profile)

    user_resp = client.post("/api/users/ensure", json={})
    user_id = user_resp.json()["user_id"]

    jd_resp = client.post("/api/jd/ingest", json={"user_id": user_id, "jd_text": "Python backend role"})
    job_spec_id = jd_resp.json()["job_spec_id"]

    cv_resp = client.post("/api/cv/ingest", json={"user_id": user_id, "cv_text": "Python APIs"})
    cv_version_id = cv_resp.json()["cv_version_id"]

    analysis_resp = client.post(
        "/api/cv/analyze",
        json={"user_id": user_id, "cv_version_id": cv_version_id, "job_spec_id": job_spec_id},
    )
    assert analysis_resp.status_code == 200
    assert 0.0 <= analysis_resp.json()["match_score"] <= 1.0

    save_resp = client.post(
        "/api/cv/save",
        json={
            "user_id": user_id,
            "updated_cv_text": "Improved Python APIs",
            "parent_cv_version_id": cv_version_id,
        },
    )
    assert save_resp.status_code == 200

    progress_resp = client.get(f"/api/progress/overview?user_id={user_id}&job_spec_id={job_spec_id}")
    assert progress_resp.status_code == 200
