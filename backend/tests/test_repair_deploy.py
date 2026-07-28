"""Tester / repair / deploy acceptance tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent.code import code_from_gamespec
from app.agent.deploy import deploy_game
from app.agent.graph import compile_game_builder_graph
from app.agent.repair import repair_game_artifact
from app.agent.state import initial_state
from app.agent.test_game import evaluate_game_artifact, run_acceptance_checks
from app.config import Settings, clear_settings_cache
from app.fixtures.mock_game import mock_orbit_run_spec
from app.main import app
from app.models import AcceptanceItem

FIXTURE_ANSWERS = {
    "twist": "near-miss recharges shields",
    "difficulty": "standard",
    "win": "clear 5 waves",
    "art": "minimal geometric",
}


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("CODE_MODE", "mock")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    clear_settings_cache()
    yield
    clear_settings_cache()


def _broken_game(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text("<html><body>broken</body></html>", encoding="utf-8")
    (root / "style.css").write_text("", encoding="utf-8")
    (root / "game.js").write_text("console.log('noop');", encoding="utf-8")


def test_acceptance_fails_on_broken_game(tmp_path):
    root = tmp_path / "artifacts" / "bad" / "game"
    _broken_game(root)
    report = run_acceptance_checks(root)
    assert report.passed is False
    assert any(it.passed is False for it in report.items)


def test_repair_then_acceptance_passes(tmp_path):
    settings = Settings(artifacts_dir=str(tmp_path / "artifacts"))
    root = tmp_path / "artifacts" / "fix-me" / "game"
    _broken_game(root)
    before = run_acceptance_checks(root)
    assert before.passed is False

    result = repair_game_artifact(
        "fix-me",
        root,
        before.model_dump(mode="json"),
        repair_count=1,
        settings=settings,
    )
    assert result["applied"]
    after = run_acceptance_checks(root)
    assert after.passed is True
    assert (tmp_path / "artifacts" / "fix-me" / "repair-log.json").is_file()


def test_budget_exhausted_ends_failed(tmp_path, monkeypatch):
    """Always-failing tests exhaust repair budget → graph ends without deploy."""
    from app.agent import nodes

    def always_fail(state):
        return {
            "status": "testing",
            "test_report": {
                "passed": False,
                "items": [{"id": "boots", "description": "game boots", "passed": False}],
                "summary": "always fail",
            },
            "test_passed": False,
            "messages": ["test: always fail"],
            "trace": [
                {"kind": "thought", "node": "test", "message": "fail"},
            ],
        }

    monkeypatch.setattr(nodes, "test_node", always_fail)
    graph = compile_game_builder_graph()
    result = graph.invoke(
        initial_state(
            "space shooter",
            run_id="budget-1",
            repair_budget=2,
            answers=FIXTURE_ANSWERS,
        ),
        config={"configurable": {"thread_id": "budget-1"}},
    )
    assert result.get("play_url") is None
    assert result["repair_count"] == 2
    assert result["test_passed"] is False
    assert result["status"] != "completed"


def test_happy_path_deploys_play_and_zip(tmp_path):
    settings = Settings(
        artifacts_dir=str(tmp_path / "artifacts"),
        code_mode="mock",
        llm_provider="mock",
    )
    clear_settings_cache()
    spec = mock_orbit_run_spec()
    root, _, _ = code_from_gamespec(spec, "ship-1", settings=settings)
    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'href="/play/ship-1/style.css"' in html
    assert 'src="/play/ship-1/game.js"' in html
    report, _ = evaluate_game_artifact(
        "ship-1",
        root,
        [AcceptanceItem(id="boots", description="game boots").model_dump()],
        settings=settings,
    )
    assert report.passed is True

    deployed = deploy_game("ship-1", root, settings=settings)
    assert deployed["play_url"] == "/play/ship-1/"
    assert Path(deployed["zip_path"]).is_file()

    client = TestClient(app)
    # Both slash variants must serve the game (Next may strip trailing slash).
    for url in ("/play/ship-1", "/play/ship-1/"):
        page = client.get(url)
        assert page.status_code == 200
        assert b"<canvas" in page.content
    asset = client.get("/play/ship-1/game.js")
    assert asset.status_code == 200
    z = client.get("/api/runs/ship-1/download")
    assert z.status_code == 200
    assert "zip" in z.headers.get("content-type", "")


def test_graph_end_to_end_play_url(tmp_path):
    graph = compile_game_builder_graph()
    result = graph.invoke(
        initial_state(
            "Make a new game like a space shooter",
            run_id="e2e-play",
            answers=FIXTURE_ANSWERS,
        ),
        config={"configurable": {"thread_id": "e2e-play"}},
    )
    assert result["status"] == "completed"
    assert result["test_passed"] is True
    assert result["play_url"] == "/play/e2e-play/"
    assert (Path(result["artifact_dir"]) / "index.html").is_file()
    zip_path = tmp_path / "artifacts" / "e2e-play" / "game.zip"
    assert zip_path.is_file()
