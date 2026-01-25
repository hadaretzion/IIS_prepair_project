import json

from backend.services import scoring


def test_score_answer_fallback(monkeypatch):
    monkeypatch.setattr(scoring, "call_gemini", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("fail")))

    result = scoring.score_answer(
        question="Explain REST",
        user_transcript="REST is stateless.",
        user_code=None,
        role_profile={},
        reference_solution=None,
        topics=["api"],
    )
    assert 0.0 <= result["overall"] <= 1.0
    assert "rubric" in result


def test_maybe_generate_followup(monkeypatch):
    response = json.dumps({"followup": "Can you give a concrete example?"})
    monkeypatch.setattr(scoring, "call_gemini", lambda *_args, **_kwargs: response)

    followup = scoring.maybe_generate_followup(
        question="Explain caching",
        transcript="Short answer",
        score_json={"overall": 0.2, "notes": ["too short"]},
        role_profile={},
    )
    assert followup == "Can you give a concrete example?"
