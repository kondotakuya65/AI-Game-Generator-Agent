"""Coder: write HTML/Canvas/JS game files from GameSpec + genre templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.models import GameSpec
from app.templates import render_genre_template


REQUIRED_FILES = ("index.html", "style.css", "game.js")


def game_dir(run_id: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.artifacts_dir) / run_id / "game"


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
) -> tuple[Path, list[str], str]:
    """
    Render genre template and write artifacts/{run_id}/game/*.

    Returns (game_dir, written_filenames, source).
    """
    spec = gamespec if isinstance(gamespec, GameSpec) else GameSpec.model_validate(gamespec)
    files = render_genre_template(spec)
    missing = [name for name in REQUIRED_FILES if name not in files]
    if missing:
        raise ValueError(f"template missing files: {missing}")
    root = write_game_files(run_id, files, settings=settings)
    return root, sorted(files.keys()), "template"
