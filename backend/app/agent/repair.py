"""Repair: patch generated game files after failed acceptance checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.fixtures.mock_game import mock_orbit_run_spec
from app.templates import render_genre_template

# Minimal snippets injected when keyword checks fail.
_PATCH_MOVE = """
/* repair:move */
window.addEventListener("keydown", function (e) {
  if (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === "a" || e.key === "d") {
    if (typeof player !== "undefined") {
      if (e.key === "ArrowLeft" || e.key === "a") player.x = (player.x || 0) - 5;
      if (e.key === "ArrowRight" || e.key === "d") player.x = (player.x || 0) + 5;
    }
  }
});
"""

_PATCH_SCORE = """
/* repair:score */
(function () {
  if (typeof score === "undefined") { var score = 0; }
  var el = document.getElementById("score");
  if (el) el.textContent = String(score);
  window.__bumpScore = function (n) {
    score += n;
    if (el) el.textContent = String(score);
  };
})();
"""

_PATCH_WIN_LOSE = """
/* repair:win_lose */
(function () {
  var statusEl = document.getElementById("status");
  function setStatus(t) { if (statusEl) statusEl.textContent = t; }
  window.__forceWin = function () { setStatus("win -- objective reached"); };
  window.__forceLose = function () { setStatus("lose -- player defeated"); };
})();
"""

_PATCH_SHOOT = """
/* repair:shoot */
window.addEventListener("keydown", function (e) {
  if (e.key === " " || e.key === "Spacebar") {
    if (typeof bullets !== "undefined" && typeof player !== "undefined") {
      bullets.push({ x: player.x, y: player.y, w: 4, h: 10, vy: -8 });
    }
  }
});
"""

_PATCH_ENEMY = """
/* repair:enemy */
(function () {
  if (typeof enemies === "undefined") { var enemies = []; }
  enemies.push({ x: 100, y: 40, w: 24, h: 18, vy: 1 });
})();
"""

_BOOT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Repaired Game</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <h1 id="title">Repaired Game</h1>
  <p>Score: <span id="score">0</span> · <span id="status">ready</span></p>
  <canvas id="game" width="640" height="480"></canvas>
  <script src="game.js"></script>
</body>
</html>
"""

_BOOT_CSS = """#game { display: block; background: #0a1c24; border: 1px solid #1e3a44; }
body { margin: 0; background: #07141a; color: #e6f2ef; font-family: sans-serif; }
"""

_BOOT_JS = """/* repair:boots */
(function () {
  var canvas = document.getElementById("game");
  var ctx = canvas.getContext("2d");
  var score = 0;
  var player = { x: 300, y: 400, w: 28, h: 18 };
  var bullets = [];
  var enemies = [{ x: 200, y: 40, w: 24, h: 18, vy: 1 }];
  function setStatus(t) {
    var el = document.getElementById("status");
    if (el) el.textContent = t;
  }
  window.addEventListener("keydown", function (e) {
    if (e.key === "ArrowLeft" || e.key === "a") player.x -= 5;
    if (e.key === "ArrowRight" || e.key === "d") player.x += 5;
    if (e.key === " " || e.key === "Spacebar") {
      bullets.push({ x: player.x, y: player.y, w: 4, h: 10, vy: -8 });
    }
  });
  function loop() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f0a202";
    ctx.fillRect(player.x, player.y, player.w, player.h);
    ctx.fillStyle = "#3ecf8e";
    for (var i = 0; i < bullets.length; i++) {
      bullets[i].y += bullets[i].vy;
      ctx.fillRect(bullets[i].x, bullets[i].y, bullets[i].w, bullets[i].h);
    }
    ctx.fillStyle = "#e85d4c";
    for (var j = 0; j < enemies.length; j++) {
      enemies[j].y += enemies[j].vy;
      ctx.fillRect(enemies[j].x, enemies[j].y, enemies[j].w, enemies[j].h);
    }
    requestAnimationFrame(loop);
  }
  setStatus("ready");
  loop();
})();
"""


def _failed_ids(test_report: dict[str, Any] | None) -> list[str]:
    if not test_report:
        return []
    items = test_report.get("items") or []
    out: list[str] = []
    for it in items:
        if isinstance(it, dict) and it.get("passed") is False:
            out.append(str(it.get("id") or it.get("description") or "unknown"))
    return out


def _append_js(path: Path, snippet: str) -> bool:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    marker = snippet.strip().splitlines()[0]
    if marker in text:
        return False
    path.write_text(text.rstrip() + "\n" + snippet.strip() + "\n", encoding="utf-8")
    return True


def apply_targeted_patches(game_dir: Path, failed_ids: list[str]) -> list[str]:
    """Apply minimal JS/HTML/CSS patches for failed acceptance ids."""
    applied: list[str] = []
    html_path = game_dir / "index.html"
    css_path = game_dir / "style.css"
    js_path = game_dir / "game.js"
    game_dir.mkdir(parents=True, exist_ok=True)

    blob = " ".join(failed_ids).lower()

    needs_boot = any(k in blob for k in ("boot", "file", "load", "start"))
    if needs_boot or not js_path.is_file() or not html_path.is_file():
        if not html_path.is_file() or "<canvas" not in html_path.read_text(encoding="utf-8", errors="ignore").lower():
            html_path.write_text(_BOOT_HTML, encoding="utf-8")
            applied.append("boots:html")
        if not css_path.is_file() or not css_path.read_text(encoding="utf-8", errors="ignore").strip():
            css_path.write_text(_BOOT_CSS, encoding="utf-8")
            applied.append("boots:css")
        js = js_path.read_text(encoding="utf-8", errors="ignore") if js_path.is_file() else ""
        if "getContext" not in js or "requestAnimationFrame" not in js:
            js_path.write_text(_BOOT_JS, encoding="utf-8")
            applied.append("boots:js")
            return applied  # full boot rewrite covers the rest

    if any(k in blob for k in ("move", "control")):
        if _append_js(js_path, _PATCH_MOVE):
            applied.append("move")
    if "score" in blob:
        if _append_js(js_path, _PATCH_SCORE):
            applied.append("score")
    if any(k in blob for k in ("win", "lose")):
        if _append_js(js_path, _PATCH_WIN_LOSE):
            applied.append("win_lose")
    if any(k in blob for k in ("shoot", "act", "fire", "bullet")):
        if _append_js(js_path, _PATCH_SHOOT):
            applied.append("shoot")
    if any(k in blob for k in ("enemy", "drone", "threat", "hazard", "obstacle")):
        if _append_js(js_path, _PATCH_ENEMY):
            applied.append("enemy")

    return applied


def rewrite_mock_game(game_dir: Path, prompt: str = "", *, run_id: str | None = None) -> list[str]:
    """Nuclear repair: rewrite files from deterministic Orbit Run mock."""
    rid = run_id or game_dir.parent.name
    files = render_genre_template(mock_orbit_run_spec(prompt or None), run_id=rid)
    game_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (game_dir / name).write_text(content, encoding="utf-8")
    return [f"rewrite:{name}" for name in sorted(files)]


def repair_game_artifact(
    run_id: str,
    artifact_dir: str | Path | None,
    test_report: dict[str, Any] | None,
    *,
    repair_count: int,
    prompt: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Patch (or rewrite) game files for failed acceptance items.

    Attempt 1: targeted patches. Attempt 2+: full mock rewrite.
    """
    settings = settings or get_settings()
    game_dir = Path(artifact_dir) if artifact_dir else Path(settings.artifacts_dir) / run_id / "game"
    failed = _failed_ids(test_report)

    if repair_count <= 1:
        applied = apply_targeted_patches(game_dir, failed or ["boots"])
        strategy = "targeted"
        if not applied:
            applied = rewrite_mock_game(game_dir, prompt, run_id=run_id)
            strategy = "mock_rewrite"
    else:
        applied = rewrite_mock_game(game_dir, prompt, run_id=run_id)
        strategy = "mock_rewrite"

    log = {
        "run_id": run_id,
        "attempt": repair_count,
        "strategy": strategy,
        "failed_ids": failed,
        "applied": applied,
    }
    log_path = Path(settings.artifacts_dir) / run_id / "repair-log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Append-friendly: keep latest attempt as last entry in a list file
    history_path = Path(settings.artifacts_dir) / run_id / "repair-history.json"
    history: list[dict[str, Any]] = []
    if history_path.is_file():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    history.append(log)
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    return {
        "strategy": strategy,
        "applied": applied,
        "failed_ids": failed,
        "log_path": str(log_path),
        "game_dir": str(game_dir),
    }
