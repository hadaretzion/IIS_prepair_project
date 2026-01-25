import json
import itertools

def test_agentic_interview_followup_no_repeat(client, sample_user, sample_job_spec, sample_cv_version, sample_questions, monkeypatch):
    followup_texts = itertools.cycle([
        "Can you walk me through a specific example?",
        "What trade-offs did you consider?",
    ])

    def fake_call_llm(system_prompt: str, user_prompt: str, prefer: str = "gemini") -> str:
        if "Analyze this interview answer" in user_prompt:
            if "FOLLOWUP_OPEN" in user_prompt or "FOLLOWUP_CODE" in user_prompt:
                return json.dumps({
                    "score": 0.85,
                    "strengths": ["Provided details"],
                    "gaps": [],
                    "followup_type": None,
                    "notes": [],
                })
            if "CODE_ANSWER" in user_prompt:
                return json.dumps({
                    "score": 0.6,
                    "strengths": ["Shows understanding"],
                    "gaps": ["Clarify edge cases"],
                    "followup_type": "probe_deeper",
                    "notes": [],
                })
            return json.dumps({
                "score": 0.6,
                "strengths": ["Relevant response"],
                "gaps": ["Needs an example"],
                "followup_type": "clarify",
                "notes": [],
            })

        if "Review the candidate code" in user_prompt:
            return json.dumps({
                "score": 0.7,
                "strengths": ["Reasonable approach"],
                "issues": [],
                "complexity": "low",
                "followup_type": None,
            })

        if "Generate a follow-up question" in user_prompt:
            return json.dumps({"followup": next(followup_texts)})

        return json.dumps({"followup": "Can you elaborate?"})

    monkeypatch.setattr("backend.services.interview_agent.call_llm", fake_call_llm)
    monkeypatch.setattr("backend.services.answer_analyzer.call_llm", fake_call_llm)
    monkeypatch.setattr("backend.services.code_evaluator.call_llm", fake_call_llm)

    start_response = client.post(
        "/api/interview/start",
        json={
            "user_id": sample_user.id,
            "job_spec_id": sample_job_spec.id,
            "cv_version_id": sample_cv_version.id,
            "mode": "direct",
            "settings": {"num_open": 1, "num_code": 1, "duration_minutes": 5},
        },
    )
    assert start_response.status_code == 200
    start_data = start_response.json()

    first_answer = client.post(
        "/api/interview/next",
        json={
            "session_id": start_data["session_id"],
            "user_transcript": "OPEN_ANSWER",
            "user_code": None,
            "is_followup": False,
            "elapsed_seconds": 12,
        },
    )
    assert first_answer.status_code == 200
    first_payload = first_answer.json()
    first_followup = first_payload["followup_question"]["text"]
    assert first_followup == "Can you walk me through a specific example?"

    followup_answer = client.post(
        "/api/interview/next",
        json={
            "session_id": start_data["session_id"],
            "user_transcript": "FOLLOWUP_OPEN",
            "user_code": None,
            "is_followup": True,
            "elapsed_seconds": 25,
        },
    )
    assert followup_answer.status_code == 200
    followup_payload = followup_answer.json()
    assert followup_payload["next_question"]

    code_answer = client.post(
        "/api/interview/next",
        json={
            "session_id": start_data["session_id"],
            "user_transcript": "CODE_ANSWER",
            "user_code": "def two_sum(nums, target): return []",
            "is_followup": False,
            "elapsed_seconds": 30,
        },
    )
    assert code_answer.status_code == 200
    code_payload = code_answer.json()
    second_followup = code_payload["followup_question"]["text"]
    assert second_followup == "What trade-offs did you consider?"
    assert second_followup != first_followup

    final_answer = client.post(
        "/api/interview/next",
        json={
            "session_id": start_data["session_id"],
            "user_transcript": "FOLLOWUP_CODE",
            "user_code": "def two_sum(nums, target): return []",
            "is_followup": True,
            "elapsed_seconds": 40,
        },
    )
    assert final_answer.status_code == 200
    final_payload = final_answer.json()
    assert final_payload["is_done"] is True
