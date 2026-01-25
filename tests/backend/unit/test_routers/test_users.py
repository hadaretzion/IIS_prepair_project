from tests.backend.fixtures.sample_data import create_user


def test_ensure_user_creates_new_user(client):
    response = client.post("/api/users/ensure", json={})
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert data["user_id"]


def test_ensure_user_returns_existing(client, db_session):
    user = create_user(db_session, user_id="existing-user")

    response = client.post("/api/users/ensure", json={"user_id": user.id})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id
