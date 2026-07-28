"""Static acceptance checks against generated HTML/Canvas/JS artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.models import AcceptanceItem, TestReport

REQUIRED_GAME_FILES = ("index.html", "style.css", "game.js")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _keywords_for_item(item: AcceptanceItem) -> tuple[str, ...]:
    desc = (item.description or "").lower()
    iid = (item.id or "").lower()
    blob = f"{iid} {desc}"

    if any(k in blob for k in ("boot", "load", "start")):
        return ("canvas", "getcontext", "requestanimationframe", "ready")
    if any(k in blob for k in ("move", "control", "wasd", "arrow")):
        return ("keydown", "arrowleft", "arrowright", "player")
    if any(k in blob for k in ("score", "point")):
        return ("score",)
    if any(k in blob for k in ("win", "lose", "defeat", "fail", "survive")):
        return ("win", "lose")
    if any(k in blob for k in ("shoot", "fire", "act", "action", "bullet")):
        return ("bullet", "space", "keydown")
    if any(k in blob for k in ("enemy", "drone", "threat")):
        return ("enem", "drone", "hazard")
    if any(k in blob for k in ("obstacle", "hazard", "lane")):
        return ("hazard", "lane")
    if any(k in blob for k in ("tile", "piece", "board", "match", "puzzle")):
        return ("tile", "click", "match")
    # generic playable loop
    return ("canvas", "score")


def _check_item(item: AcceptanceItem, html: str, css: str, js: str) -> AcceptanceItem:
    lower_html = html.lower()
    lower_js = js.lower()
    lower_all = f"{lower_html}\n{css.lower()}\n{lower_js}"
    desc = (item.description or "").lower()
    iid = (item.id or "").lower()

    # Structural boots check
    if any(k in f"{iid} {desc}" for k in ("boot", "load", "start")):
        ok = (
            "<canvas" in lower_html
            and 'id="game"' in lower_html
            and "getcontext" in lower_js
            and bool(css.strip())
        )
        detail = "canvas shell + getContext + css" if ok else "missing canvas shell pieces"
        return item.model_copy(update={"passed": ok, "detail": detail})

    keywords = _keywords_for_item(item)
    hits = [k for k in keywords if k in lower_all]
    ok = len(hits) > 0
    detail = f"matched: {', '.join(hits)}" if ok else f"missing any of: {', '.join(keywords)}"
    return item.model_copy(update={"passed": ok, "detail": detail})


def normalize_acceptance_items(raw: list[Any] | None) -> list[AcceptanceItem]:
    items: list[AcceptanceItem] = []
    for i, entry in enumerate(raw or []):
        if isinstance(entry, AcceptanceItem):
            items.append(entry)
        elif isinstance(entry, dict):
            items.append(AcceptanceItem.model_validate(entry))
        elif isinstance(entry, str) and entry.strip():
            slug = re.sub(r"[^a-z0-9]+", "_", entry.lower()).strip("_") or f"item_{i}"
            items.append(AcceptanceItem(id=slug, description=entry))
    if not items:
        items = [
            AcceptanceItem(id="boots", description="game boots"),
            AcceptanceItem(id="move", description="player can move"),
            AcceptanceItem(id="score", description="score updates"),
            AcceptanceItem(id="win_lose", description="win or lose reachable"),
            AcceptanceItem(id="act", description="player can act"),
        ]
    return items


def run_acceptance_checks(
    game_path: Path | str,
    acceptance: list[Any] | None = None,
) -> TestReport:
    root = Path(game_path)
    items = normalize_acceptance_items(acceptance)

    missing = [name for name in REQUIRED_GAME_FILES if not (root / name).is_file()]
    if missing:
        failed = [
            AcceptanceItem(
                id="files",
                description="required game files present",
                passed=False,
                detail=f"missing: {', '.join(missing)}",
            )
        ]
        return TestReport(
            passed=False,
            items=failed + [it.model_copy(update={"passed": False, "detail": "skipped"}) for it in items],
            summary=f"Missing files: {', '.join(missing)}",
        )

    html = _read(root / "index.html")
    css = _read(root / "style.css")
    js = _read(root / "game.js")

    checked = [_check_item(it, html, css, js) for it in items]
    passed = all(it.passed for it in checked)
    failed_ids = [it.id for it in checked if not it.passed]
    summary = (
        f"All {len(checked)} acceptance checks passed."
        if passed
        else f"Failed: {', '.join(failed_ids)}"
    )
    return TestReport(passed=passed, items=checked, summary=summary)


def write_test_report(
    run_id: str,
    report: TestReport,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    root = Path(settings.artifacts_dir) / run_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / "test-report.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def evaluate_game_artifact(
    run_id: str,
    artifact_dir: str | Path | None,
    acceptance: list[Any] | None = None,
    *,
    settings: Settings | None = None,
) -> tuple[TestReport, Path]:
    settings = settings or get_settings()
    game_path = Path(artifact_dir) if artifact_dir else Path(settings.artifacts_dir) / run_id / "game"
    report = run_acceptance_checks(game_path, acceptance)
    path = write_test_report(run_id, report, settings=settings)
    return report, path
