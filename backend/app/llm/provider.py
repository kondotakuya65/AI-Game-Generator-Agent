"""LLM provider adapter: ollama | openai | anthropic | mock."""

from __future__ import annotations

import json
from typing import Protocol

import httpx

from app.config import Settings, get_settings


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class MockLLMClient:
    """Deterministic replies for tests / offline demos."""

    def complete(self, system: str, user: str) -> str:
        sys_l = system.lower()
        lower = user.lower()

        # Clarify before GameSpec — clarify prompts mention GameSpec as "do not lock yet".
        if "uniqueness questions" in sys_l or (
            "clarif" in sys_l and "question" in sys_l
        ):
            return json.dumps(
                {
                    "questions": [
                        {
                            "id": "twist",
                            "text": "What unique twist should set this shooter apart?",
                            "options": [
                                "near-miss recharges shields",
                                "gravity wells pull shots",
                                "only sideways movement",
                            ],
                        },
                        {
                            "id": "difficulty",
                            "text": "Target difficulty?",
                            "options": ["casual", "standard", "hard"],
                        },
                        {
                            "id": "win",
                            "text": "How does the player win?",
                            "options": ["survive 60s", "clear 5 waves", "defeat boss"],
                        },
                        {
                            "id": "art",
                            "text": "Art vibe?",
                            "options": ["neon vectors", "minimal geometric", "retro pixel"],
                        },
                    ]
                }
            )

        # Designer before GameSpec lock — design prompts also mention GameSpec.
        if (
            "mechanics:" in sys_l
            or "mechanics plan" in sys_l
            or "game designer" in sys_l
            or "assets:" in sys_l
        ):
            return (
                "MECHANICS: Arrow keys move; space fires upward bolts; "
                "near-misses recharge shields; waves escalate drone count.\n"
                "ASSETS: Rect ship, triangle drones, circle bolts — canvas only.\n"
                "ACCEPTANCE: boots; move; shoot; enemy; score; win/lose."
            )

        if "gamespec" in sys_l or ("lock" in sys_l and "spec" in sys_l):
            return json.dumps(
                {
                    "genre": "shooter",
                    "title": "Orbit Run",
                    "twist": "shields recharge on near-miss",
                    "prompt": user.strip()[:200] or "space shooter",
                    "controls": {"move": "arrows", "action": "space", "notes": ""},
                    "entities": [
                        {"id": "player", "role": "player", "behavior": "ship", "count": 1},
                        {"id": "drone", "role": "enemy", "behavior": "descend", "count": 8},
                        {"id": "bolt", "role": "projectile", "behavior": "up", "count": None},
                    ],
                    "win_lose": {"win": "clear 5 waves", "lose": "hull reaches 0"},
                    "scoring": {"events": ["enemy destroyed +100"], "win_score": None},
                    "visual": {
                        "palette": ["#07141a", "#f0a202", "#3ecf8e"],
                        "art_vibe": "minimal geometric",
                        "notes": "",
                    },
                    "acceptance": [
                        "game boots",
                        "player can move",
                        "player can shoot",
                        "enemy exists",
                        "score updates",
                        "win or lose reachable",
                    ],
                }
            )

        if "repair" in sys_l or "patch" in sys_l:
            return (
                "// mock repair: ensure score increments on enemy hit\n"
                "Mock LLM: apply minimal patch to satisfy failing acceptance item."
            )

        if "code" in sys_l or "html" in lower or "canvas" in sys_l:
            return (
                "Mock LLM: emit HTML/Canvas/JS via coder templates in a later phase. "
                "Genre=shooter twist=near-miss shields."
            )

        return (
            "Mock LLM: game generator online. "
            "Clarify uniqueness, lock GameSpec, then design → code → test → deploy."
        )


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_predict": 1024},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("message", {}).get("content", "")


class OpenAIClient:
    def __init__(self, api_key: str, model: str, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 1200,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


class AnthropicClient:
    def __init__(self, api_key: str, model: str, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 1200,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        blocks = data.get("content") or []
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return "\n".join(texts).strip()


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()
    timeout = settings.llm_timeout_seconds
    if provider == "mock":
        return MockLLMClient()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAIClient(settings.openai_api_key, settings.openai_model, timeout=timeout)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return AnthropicClient(
            settings.anthropic_api_key,
            settings.anthropic_model,
            timeout=timeout,
        )
    if provider == "ollama":
        return OllamaClient(settings.ollama_base_url, settings.ollama_model, timeout=timeout)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
