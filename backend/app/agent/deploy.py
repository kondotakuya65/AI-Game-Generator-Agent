"""Deploy: prepare play URL + zip download for a generated game."""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.config import Settings, get_settings

GAME_FILES = ("index.html", "style.css", "game.js")


def game_dir_for(
    run_id: str,
    artifact_dir: str | Path | None = None,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    if artifact_dir:
        path = Path(artifact_dir)
        if path.name == "game":
            return path
        candidate = path / "game"
        return candidate if candidate.is_dir() else path
    return Path(settings.artifacts_dir) / run_id / "game"


def play_url_for(run_id: str) -> str:
    return f"/play/{run_id}/"


def zip_path_for(run_id: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.artifacts_dir) / run_id / "game.zip"


def create_game_zip(
    run_id: str,
    artifact_dir: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    root = game_dir_for(run_id, artifact_dir, settings)
    if not root.is_dir():
        raise FileNotFoundError(f"game directory not found: {root}")

    out = zip_path_for(run_id, settings)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in GAME_FILES:
            path = root / name
            if path.is_file():
                zf.write(path, arcname=name)
        # include any extra files in the game folder
        for path in root.iterdir():
            if path.is_file() and path.name not in GAME_FILES:
                zf.write(path, arcname=path.name)
    return out


def deploy_game(
    run_id: str,
    artifact_dir: str | Path | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, str]:
    """Create zip and return play/download URLs."""
    settings = settings or get_settings()
    root = game_dir_for(run_id, artifact_dir, settings)
    if not (root / "index.html").is_file():
        raise FileNotFoundError(f"index.html missing in {root}")

    zip_file = create_game_zip(run_id, root, settings=settings)
    play_url = play_url_for(run_id)
    download_url = f"/api/runs/{run_id}/download"
    return {
        "play_url": play_url,
        "download_url": download_url,
        "zip_path": str(zip_file),
        "game_dir": str(root),
    }
