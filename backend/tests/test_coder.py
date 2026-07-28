"""Coder + genre template artifact tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.code import REQUIRED_FILES, code_from_gamespec, resolve_code_mode
from app.agent.graph import compile_game_builder_graph
from app.agent.state import initial_state
from app.config import Settings, clear_settings_cache
from app.models import EntitySpec, GameSpec, Genre, WinLoseSpec
from app.templates import SUPPORTED_GENRES, render_genre_template

FIXTURE_ANSWERS = {
    "twist": "near-miss recharges shields",
    "difficulty": "standard",
    "win": "clear 5 waves",
    "art": "minimal geometric",
}


def _spec(genre: Genre = Genre.SHOOTER, **overrides) -> GameSpec:
    base = dict(
        genre=genre,
        title=f"Test {genre.value}",
        twist="unique twist",
        prompt=f"make a {genre.value}",
        win_lose=WinLoseSpec(win="win condition", lose="lose condition"),
        entities=[EntitySpec(id="player", role="player")],
    )
    base.update(overrides)
    return GameSpec(**base)


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("CODE_MODE", "mock")
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_supported_genres():
    assert set(SUPPORTED_GENRES) == {"shooter", "runner", "puzzle"}


def test_each_genre_template_has_canvas_shell():
    for genre in Genre:
        files = render_genre_template(_spec(genre))
        assert set(files) == set(REQUIRED_FILES)
        html = files["index.html"]
        assert "<canvas" in html
        assert 'id="game"' in html
        assert "game.js" in html
        assert "getContext" in files["game.js"]
        assert "canvas" in files["style.css"] or "#game" in files["style.css"]


def test_mock_coder_writes_required_files(tmp_path):
    root, names, source = code_from_gamespec(
        _spec(Genre.PUZZLE, title="Ignored Title"),
        "coder-mock-1",
    )
    assert source == "mock"
    assert set(names) == set(REQUIRED_FILES)
    for name in REQUIRED_FILES:
        path = root / name
        assert path.is_file()
        assert path.stat().st_size > 0
    html = (root / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "<canvas" in html
    assert "Orbit Run" in html  # mock fixture title


def test_mock_coder_is_deterministic(tmp_path):
    a, _, _ = code_from_gamespec(_spec(Genre.RUNNER), "det-a")
    b, _, _ = code_from_gamespec(_spec(Genre.PUZZLE), "det-b")
    assert (a / "game.js").read_text(encoding="utf-8") == (b / "game.js").read_text(
        encoding="utf-8"
    )


def test_template_mode_uses_locked_genre(tmp_path, monkeypatch):
    monkeypatch.setenv("CODE_MODE", "template")
    clear_settings_cache()
    root, _, source = code_from_gamespec(_spec(Genre.RUNNER, title="Lane Rush"), "tmpl-1")
    assert source == "template"
    js = (root / "game.js").read_text(encoding="utf-8")
    assert "Genre: runner" in js
    assert "Lane Rush" in (root / "index.html").read_text(encoding="utf-8")


def test_resolve_code_mode_auto():
    assert resolve_code_mode(Settings(llm_provider="mock", code_mode="auto")) == "mock"
    assert resolve_code_mode(Settings(llm_provider="ollama", code_mode="auto")) == "template"


def test_graph_code_node_writes_game_dir(tmp_path):
    graph = compile_game_builder_graph()
    result = graph.invoke(
        initial_state(
            "Make a new game like a space shooter",
            run_id="coder-graph-1",
            answers=FIXTURE_ANSWERS,
        ),
        config={"configurable": {"thread_id": "coder-graph-1"}},
    )
    artifact = Path(result["artifact_dir"])
    assert artifact.is_dir()
    assert (artifact / "index.html").is_file()
    assert (artifact / "game.js").is_file()
    assert (artifact / "style.css").is_file()
    html = (artifact / "index.html").read_text(encoding="utf-8")
    assert "<canvas" in html
