"""Coder: write HTML/Canvas/JS game files from GameSpec + genre templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.config import Settings, get_settings
from app.fixtures.mock_game import mock_orbit_run_spec
from app.models import GameSpec
from app.templates import render_genre_template

REQUIRED_FILES = ("index.html", "style.css", "game.js")
CodeSource = Literal["mock", "template"]


def game_dir(run_id: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.artifacts_dir) / run_id / "game"


def resolve_code_mode(settings: Settings | None = None) -> Literal["mock", "template"]:
    """
    CODE_MODE=auto → mock when LLM_PROVIDER=mock (offline demos), else template.
    Explicit mock|template always wins.
    """
    settings = settings or get_settings()
    mode = (settings.code_mode or "auto").lower()
    if mode == "mock":
        return "mock"
    if mode == "template":
        return "template"
    # auto
    if settings.llm_provider.lower() == "mock":
        return "mock"
    return "template"


def write_game_files(
    run_id: str,
    files: dict[str, str],
    settings: Settings | None = None,
) -> Path:
    root = game_dir(run_id, settings)
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    return root


def code_from_gamespec(
    gamespec: dict[str, Any] | GameSpec,
    run_id: str,
    *,
    settings: Settings | None = None,
    code_mode: str | None = None,
) -> tuple[Path, list[str], CodeSource]:
    """
    Render genre template and write artifacts/{run_id}/game/*.

    Mock mode ignores most of the locked spec and uses fixed Orbit Run so
    offline demos stay byte-stable.

    Returns (game_dir, written_filenames, source).
    """
    settings = settings or get_settings()
    mode = (code_mode or resolve_code_mode(settings)).lower()
    locked = gamespec if isinstance(gamespec, GameSpec) else GameSpec.model_validate(gamespec)

    if mode == "mock":
        spec = mock_orbit_run_spec(prompt=locked.prompt)
        source: CodeSource = "mock"
    else:
        spec = locked
        source = "template"

    files = render_genre_template(spec)
    missing = [name for name in REQUIRED_FILES if name not in files]
    if missing:
        raise ValueError(f"template missing files: {missing}")
    root = write_game_files(run_id, files, settings=settings)
    return root, sorted(files.keys()), source
