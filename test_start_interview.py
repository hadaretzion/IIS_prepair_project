import requests

url = "http://localhost:8000/api/interview/start"
data = {
    "user_id": "aadbea99-8b56-4df2-8192-41a72e42785e",
    "job_spec_id": "a5ec90f8-2ba3-4266-8aa1-3b9f9747ecc3",
    "cv_version_id": "08ba3902-e40d-41e3-8318-5f32fca17c16",
    "mode": "direct",
    "settings": {
        "num_open": 4,
        "num_code": 2,
        "duration_minutes": 12,
        "persona": "friendly"
    }
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✓ Interview started successfully!")
    print(f"Session ID: {result.get('session_id')}")
else:
    print(f"✗ Error: {response.text}")
