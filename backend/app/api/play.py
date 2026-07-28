"""Serve playable games and zip downloads."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.agent.deploy import create_game_zip, game_dir_for, zip_path_for
from app.config import get_settings

play_router = APIRouter(tags=["play"])
download_router = APIRouter(prefix="/runs", tags=["runs"])


def _safe_game_file(run_id: str, filename: str) -> Path:
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=400, detail="invalid run_id")
    if ".." in filename or filename.startswith(("/", "\\")):
        raise HTTPException(status_code=400, detail="invalid path")
    root = game_dir_for(run_id)
    target = (root / filename).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return target


@play_router.get("/play/{run_id}")
@play_router.get("/play/{run_id}/")
def play_index(run_id: str) -> FileResponse:
    """Serve index at both slash variants (Next may strip trailing slashes)."""
    path = _safe_game_file(run_id, "index.html")
    return FileResponse(path, media_type="text/html")


@play_router.get("/play/{run_id}/{filename}")
def play_asset(run_id: str, filename: str) -> FileResponse:
    path = _safe_game_file(run_id, filename)
    media = {
        "html": "text/html",
        "css": "text/css",
        "js": "text/javascript",
        "json": "application/json",
        "png": "image/png",
        "svg": "image/svg+xml",
    }.get(path.suffix.lstrip(".").lower(), "application/octet-stream")
    return FileResponse(path, media_type=media)


@download_router.get("/{run_id}/download")
def download_zip(run_id: str) -> FileResponse:
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=400, detail="invalid run_id")
    settings = get_settings()
    zpath = zip_path_for(run_id, settings)
    if not zpath.is_file():
        try:
            zpath = create_game_zip(run_id, settings=settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        zpath,
        media_type="application/zip",
        filename=f"{run_id}-game.zip",
    )
