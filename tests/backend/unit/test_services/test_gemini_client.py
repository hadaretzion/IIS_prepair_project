import types

import pytest

from backend.services import gemini_client


def test_get_gemini_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert gemini_client.get_gemini_api_key() == "test-key"


def test_call_gemini_requires_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_client, "get_gemini_api_key", lambda: None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        gemini_client.call_gemini("system", "user")


def test_call_gemini_returns_text(monkeypatch):
    monkeypatch.setattr(gemini_client, "get_gemini_api_key", lambda: "fake-key")

    def fake_configure(**_kwargs):
        return None

    class DummyModel:
        def generate_content(self, _prompt, **_kwargs):
            return types.SimpleNamespace(text="ok")

    monkeypatch.setattr(gemini_client.genai, "configure", fake_configure)
    monkeypatch.setattr(gemini_client.genai, "GenerativeModel", lambda _name: DummyModel())

    assert gemini_client.call_gemini("system", "user") == "ok"
