"""SSE trace streaming tests for create → confirm pipeline."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.main import app
from app.runs.service import clear_runs

GOLDEN_PROMPT = "Make a new game like a space shooter."
GOLDEN_ANSWERS = {
    "twist": "near-miss recharges shields",
    "difficulty": "standard",
    "win": "clear 5 waves",
    "art": "minimal geometric",
}


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("CODE_MODE", "mock")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    clear_settings_cache()
    clear_runs()
    yield
    clear_runs()
    clear_settings_cache()


def _parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    for block in text.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:") :].strip()
                if payload:
                    events.append(json.loads(payload))
    return events


def test_create_stream_emits_clarify_interrupt():
    client = TestClient(app)
    res = client.post("/api/runs/stream", json={"prompt": GOLDEN_PROMPT})
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    events = _parse_sse(res.text)
    types = [e.get("type") for e in events]
    assert "status" in types
    # Clarify interrupts before the node returns, so traces land after confirm.
    assert "interrupt" in types
    assert "done" in types
    interrupt = next(e for e in events if e["type"] == "interrupt")
    assert interrupt["interrupt"]["type"] == "clarify"
    assert len(interrupt["interrupt"]["questions"]) >= 3
    done = next(e for e in events if e["type"] == "done")
    assert done["status"] == "awaiting_clarify"


def test_confirm_stream_emits_pipeline_traces():
    client = TestClient(app)
    created = client.post("/api/runs/stream", json={"prompt": GOLDEN_PROMPT})
    events = _parse_sse(created.text)
    run_id = next(e["run_id"] for e in events if e.get("type") == "status")

    res = client.post(
        f"/api/runs/{run_id}/confirm/stream",
        json={"answers": GOLDEN_ANSWERS},
    )
    assert res.status_code == 200
    events = _parse_sse(res.text)
    types = [e.get("type") for e in events]
    assert "trace" in types
    assert "done" in types
    traces = [e for e in events if e.get("type") == "trace"]
    kinds = {t.get("kind") for t in traces}
    assert {"thought", "action", "observation"}.issubset(kinds)
    nodes = {t.get("node") for t in traces}
    assert {"lock_spec", "design", "code", "test", "deploy"}.issubset(nodes)
    done = next(e for e in events if e["type"] == "done")
    assert done["status"] == "completed"
    assert done["state"]["play_url"]
    assert done["state"]["spec_locked"] is True
