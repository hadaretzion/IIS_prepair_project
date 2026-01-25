from backend.models import CVVersion
from tests.backend.fixtures.sample_data import create_cv_version, create_job_spec, create_user


def test_ingest_cv_requires_user(client):
    response = client.post(
        "/api/cv/ingest",
        json={"user_id": "missing-user", "cv_text": "Sample CV"},
    )
    assert response.status_code == 404


def test_ingest_cv_success(client, db_session):
    user = create_user(db_session, user_id="user-1")
    response = client.post(
        "/api/cv/ingest",
        json={"user_id": user.id, "cv_text": "Experienced backend engineer."},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cv_version_id" in data

    stored = db_session.get(CVVersion, data["cv_version_id"])
    assert stored is not None
    assert stored.user_id == user.id


def test_analyze_cv_success(client, db_session):
    user = create_user(db_session, user_id="user-2")
    job_spec = create_job_spec(db_session, job_spec_id="job-2")
    cv_version = create_cv_version(db_session, user_id=user.id, cv_text="Python REST APIs")

    response = client.post(
        "/api/cv/analyze",
        json={
            "user_id": user.id,
            "cv_version_id": cv_version.id,
            "job_spec_id": job_spec.id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert 0.0 <= data["match_score"] <= 1.0
    assert isinstance(data["strengths"], list)
    assert isinstance(data["gaps"], list)
    assert isinstance(data["suggestions"], list)


def test_save_cv_success(client, db_session):
    user = create_user(db_session, user_id="user-3")
    parent = create_cv_version(db_session, user_id=user.id, cv_text="Original CV")

    response = client.post(
        "/api/cv/save",
        json={
            "user_id": user.id,
            "updated_cv_text": "Updated CV",
            "parent_cv_version_id": parent.id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "new_cv_version_id" in data
    stored = db_session.get(CVVersion, data["new_cv_version_id"])
    assert stored is not None
    assert stored.parent_cv_version_id == parent.id
