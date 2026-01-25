import requests
import time

url_start = "http://localhost:8000/api/interview/start"
data_start = {
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

response = requests.post(url_start, json=data_start)
print(f"Start Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    session_id = result.get('session_id')
    print(f"✓ Interview started. Session ID: {session_id}")
    
    # Now call next
    url_next = "http://localhost:8000/api/interview/next"
    data_next = {
        "session_id": session_id,
        "user_transcript": "I am a collaborative team player with strong python skills.",
        "elapsed_seconds": 15
    }
    
    print("Sending answer...")
    response_next = requests.post(url_next, json=data_next)
    print(f"Next Status: {response_next.status_code}")
    if response_next.status_code == 200:
        next_result = response_next.json()
        print(f"Interviewer Message: {next_result.get('interviewer_message')}")
        print(f"Followup Question: {next_result.get('followup_question', {}).get('text')}")
        print(f"Next Question: {next_result.get('next_question', {}).get('text')}")
    else:
        print(f"Next Error: {response_next.text}")

else:
    print(f"Start Error: {response.text}")
