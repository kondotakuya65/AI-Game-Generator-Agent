"""Golden clarify → confirm → locked GameSpec (API + disk)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.main import app
from app.models import GameSpec
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
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    clear_settings_cache()
    clear_runs()
    yield
    clear_runs()
    clear_settings_cache()


def test_golden_space_shooter_locks_gamespec_via_api(tmp_path):
    client = TestClient(app)

    created = client.post("/api/runs", json={"prompt": GOLDEN_PROMPT})
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "awaiting_clarify"
    assert body["interrupt"]["type"] == "clarify"
    questions = body["interrupt"]["questions"]
    assert 3 <= len(questions) <= 5
    ids = {q["id"] for q in questions}
    assert "twist" in ids

    run_id = body["run_id"]
    confirmed = client.post(
        f"/api/runs/{run_id}/confirm",
        json={"answers": GOLDEN_ANSWERS},
    )
    assert confirmed.status_code == 200
    done = confirmed.json()
    assert done["status"] == "completed"
    assert done["state"]["spec_locked"] is True

    raw_spec = done["state"]["gamespec"]
    spec = GameSpec.model_validate(raw_spec)
    assert spec.genre.value == "shooter"
    assert spec.title
    assert "near-miss" in spec.twist
    assert spec.win_lose.win == "clear 5 waves"
    assert spec.visual.art_vibe == "minimal geometric"
    assert any(e.role == "player" for e in spec.entities)
    assert len(spec.acceptance) >= 4
    assert any("boot" in a.lower() or "move" in a.lower() for a in spec.acceptance)

    path = Path(tmp_path) / "artifacts" / run_id / "gamespec.json"
    assert path.is_file()
    disk = GameSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert disk.title == spec.title
    assert disk.twist == spec.twist


def test_confirm_requires_answers():
    client = TestClient(app)
    created = client.post("/api/runs", json={"prompt": GOLDEN_PROMPT}).json()
    run_id = created["run_id"]
    bad = client.post(f"/api/runs/{run_id}/confirm", json={"answers": {}})
    assert bad.status_code == 422
