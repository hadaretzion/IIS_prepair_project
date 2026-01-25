def test_ingest_jd_creates_job_spec(client):
    response = client.post(
        "/api/jd/ingest",
        json={"user_id": "user-1", "jd_text": "Looking for Python developer."},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_spec_id" in data
    assert data["jd_hash"]


def test_ingest_jd_returns_existing(client):
    payload = {"user_id": "user-1", "jd_text": "Same JD text"}
    first = client.post("/api/jd/ingest", json=payload)
    second = client.post("/api/jd/ingest", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["job_spec_id"] == second.json()["job_spec_id"]


def test_get_jd(client):
    ingest = client.post(
        "/api/jd/ingest",
        json={"user_id": "user-1", "jd_text": "Python engineer role"},
    )
    job_spec_id = ingest.json()["job_spec_id"]

    response = client.get(f"/api/jd/{job_spec_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_spec_id


def test_ingest_jd_pdf_rejects_non_pdf(client):
    files = {"file": ("jd.txt", b"Not a pdf", "text/plain")}
    data = {"user_id": "user-1"}
    response = client.post("/api/jd/ingest-pdf", files=files, data=data)
    assert response.status_code == 400
