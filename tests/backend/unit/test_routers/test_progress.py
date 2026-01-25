from backend.models import UserReadinessSnapshot
from tests.backend.fixtures.sample_data import create_job_spec, create_user


def test_progress_overview_returns_snapshot(client, db_session):
    user = create_user(db_session, user_id="user-prog")
    job_spec = create_job_spec(db_session, job_spec_id="job-prog")
    snapshot = UserReadinessSnapshot(
        user_id=user.id,
        job_spec_id=job_spec.id,
        readiness_score=75.0,
        cv_score=70.0,
        interview_score=80.0,
        practice_score=60.0,
        breakdown_json='{"cv_score": 70, "interview_score": 80, "practice_score": 60}',
    )
    db_session.add(snapshot)
    db_session.commit()

    response = client.get(f"/api/progress/overview?user_id={user.id}&job_spec_id={job_spec.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["latest_snapshot"]["readiness_score"] == 75.0
