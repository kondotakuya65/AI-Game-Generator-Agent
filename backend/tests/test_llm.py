"""LLM adapter unit tests (no live network)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings, clear_settings_cache
from app.llm.provider import (
    AnthropicClient,
    MockLLMClient,
    OllamaClient,
    OpenAIClient,
    get_llm_client,
)
from app.models import GameSpec


@pytest.fixture(autouse=True)
def _clear_settings():
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_mock_complete_default():
    text = MockLLMClient().complete("sys", "hello")
    assert "Mock LLM" in text
    assert "GameSpec" in text or "game generator" in text.lower()


def test_mock_complete_clarify_questions():
    raw = MockLLMClient().complete(
        "You ask uniqueness questions for a game.",
        "Make a space shooter",
    )
    data = json.loads(raw)
    assert "questions" in data
    assert len(data["questions"]) >= 3
    assert data["questions"][0]["id"]


def test_mock_complete_gamespec_parses():
    raw = MockLLMClient().complete(
        "Lock GameSpec JSON from answers.",
        "Make a new game like a space shooter",
    )
    data = json.loads(raw)
    spec = GameSpec.model_validate(data)
    assert spec.genre.value == "shooter"
    assert spec.title
    assert any(e.role == "player" for e in spec.entities)
    assert len(spec.acceptance) >= 4


def test_mock_complete_design_plan():
    text = MockLLMClient().complete(
        "Write a mechanics plan for the game.",
        "Orbit Run",
    )
    assert "MECHANICS" in text
    assert "ACCEPTANCE" in text


def test_get_llm_client_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    clear_settings_cache()
    client = get_llm_client()
    assert isinstance(client, MockLLMClient)


def test_get_llm_client_openai_requires_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    clear_settings_cache()
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_llm_client()


def test_get_llm_client_anthropic_requires_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    clear_settings_cache()
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_llm_client()


def test_get_llm_client_unsupported(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "watson")
    clear_settings_cache()
    with pytest.raises(ValueError, match="Unsupported"):
        get_llm_client()


def test_ollama_client_posts_chat(monkeypatch):
    calls: list[tuple[str, dict]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"message": {"content": "ollama-ok"}}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url: str, json: dict | None = None):
            calls.append((url, json or {}))
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    out = OllamaClient("http://localhost:11434", "phi3:mini", timeout=5).complete(
        "sys", "user"
    )
    assert out == "ollama-ok"
    assert calls[0][0].endswith("/api/chat")
    assert calls[0][1]["model"] == "phi3:mini"
    assert "format" not in calls[0][1]

    out_json = OllamaClient("http://localhost:11434", "phi3:mini", timeout=5).complete(
        "sys", "user", json_mode=True
    )
    assert out_json == "ollama-ok"
    assert calls[1][1].get("format") == "json"
    assert calls[1][1]["options"]["num_predict"] == 1536


def test_openai_client_posts_completions(monkeypatch):
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "openai-ok"}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url: str, headers=None, json=None):
            assert "Authorization" in headers
            assert url.endswith("/chat/completions")
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    out = OpenAIClient("sk-test", "gpt-4o-mini").complete("sys", "user")
    assert out == "openai-ok"


def test_anthropic_client_posts_messages(monkeypatch):
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"content": [{"type": "text", "text": "anthropic-ok"}]}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url: str, headers=None, json=None):
            assert headers["x-api-key"] == "ak-test"
            assert "system" in json
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    out = AnthropicClient("ak-test", "claude-3-5-haiku-latest").complete("sys", "user")
    assert out == "anthropic-ok"


def test_settings_timeout_passed_to_factory(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")
    clear_settings_cache()
    settings = Settings()
    client = get_llm_client(settings)
    assert isinstance(client, OllamaClient)
    assert client.timeout == 12.5
