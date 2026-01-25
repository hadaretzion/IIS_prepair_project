import json

from backend.services import role_profile


def test_extract_role_profile_parses_gemini(monkeypatch):
    payload = {
        "role_title": "Backend Engineer",
        "seniority": "senior",
        "must_have_topics": ["Python", "APIs"],
        "nice_to_have_topics": ["Docker"],
        "soft_skills": ["Communication"],
        "coding_focus": ["Backend"],
        "weights": {"Python": 0.9, "APIs": 0.8},
    }
    monkeypatch.setattr(
        role_profile,
        "call_gemini",
        lambda _system, _user: json.dumps(payload),
    )

    result = role_profile.extract_role_profile("cv text", "jd text")
    assert result["role_title"] == "Backend Engineer"
    assert result["seniority"] == "senior"
    assert "Python" in result["weights"]


def test_extract_role_profile_fallback(monkeypatch):
    def raise_error(_system, _user):
        raise ValueError("fail")

    monkeypatch.setattr(role_profile, "call_gemini", raise_error)
    result = role_profile.extract_role_profile("", "We need Python and AWS.")
    assert result["role_title"] == "Software Developer"
    assert "python" in [t.lower() for t in result["must_have_topics"]]
