"""Designer + acceptance checklist coverage tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent.acceptance import build_acceptance_checklist
from app.agent.design import design_from_gamespec
from app.agent.graph import compile_game_builder_graph
from app.agent.state import initial_state
from app.config import clear_settings_cache
from app.models import EntitySpec, GameSpec, Genre, WinLoseSpec

FIXTURE_ANSWERS = {
    "twist": "near-miss recharges shields",
    "difficulty": "standard",
    "win": "clear 5 waves",
    "art": "minimal geometric",
}


def _shooter_spec(**overrides) -> GameSpec:
    base = dict(
        genre=Genre.SHOOTER,
        title="Orbit Run",
        twist="near-miss recharges shields",
        prompt="Make a new game like a space shooter",
        win_lose=WinLoseSpec(win="clear 5 waves", lose="hull reaches 0"),
        entities=[
            EntitySpec(id="player", role="player", behavior="ship", count=1),
            EntitySpec(id="drone", role="enemy", behavior="descend", count=8),
        ],
        acceptance=["game boots", "player can move"],
    )
    base.update(overrides)
    return GameSpec(**base)


def _descriptions(items) -> str:
    return " ".join(it.description.lower() for it in items)


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_acceptance_checklist_covers_required_fields():
    items = build_acceptance_checklist(_shooter_spec())
    assert len(items) >= 5
    blob = _descriptions(items)
    assert "boot" in blob
    assert "move" in blob
    assert "score" in blob
    assert "win" in blob or "lose" in blob
    assert "shoot" in blob or "act" in blob or "enemy" in blob


def test_acceptance_fills_gaps_when_seeds_empty():
    items = build_acceptance_checklist(_shooter_spec(acceptance=[]))
    assert len(items) >= 5
    ids = {it.id for it in items}
    assert {"boots", "move", "score", "win_lose"}.issubset(ids)


def test_design_from_gamespec_writes_artifacts(tmp_path):
    plan, paths, source = design_from_gamespec(_shooter_spec(), "design-test-1")
    assert source in {"llm", "fallback"}
    assert len(plan.mechanics) >= 20
    assert plan.asset_plan
    assert len(plan.acceptance_tests) >= 5
    for key in ("design_md", "design_json", "acceptance_json"):
        assert Path(paths[key]).is_file()
    saved = json.loads(Path(paths["acceptance_json"]).read_text(encoding="utf-8"))
    assert len(saved) == len(plan.acceptance_tests)


def test_graph_design_node_emits_acceptance_tests():
    graph = compile_game_builder_graph()
    result = graph.invoke(
        initial_state(
            "Make a new game like a space shooter",
            run_id="design-graph-1",
            answers=FIXTURE_ANSWERS,
        ),
        config={"configurable": {"thread_id": "design-graph-1"}},
    )
    assert result["spec_locked"] is True
    assert result.get("design")
    assert len(result.get("acceptance_tests") or []) >= 5
    blob = " ".join(
        (it.get("description") or "").lower() for it in result["acceptance_tests"]
    )
    assert "boot" in blob and "move" in blob and "score" in blob
