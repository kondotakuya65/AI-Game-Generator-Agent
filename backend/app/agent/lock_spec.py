"""Lock a validated GameSpec from prompt + clarify answers; persist JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.agent.clarify import infer_genre_hint
from app.config import Settings, get_settings
from app.llm.provider import LLMClient, get_llm_client
from app.models import (
    ControlScheme,
    EntitySpec,
    GameSpec,
    Genre,
    ScoringSpec,
    VisualSpec,
    WinLoseSpec,
)

LOCK_SYSTEM = """You lock a GameSpec JSON for an HTML5 Canvas game.
Return ONLY valid JSON matching GameSpec fields:
genre (shooter|runner|puzzle), title, twist, prompt, controls, entities,
win_lose, scoring, visual, acceptance (checklist strings).
Incorporate the player's answers into twist, win_lose, visual.art_vibe.
entities must include one role=player. acceptance must list at least boots, move, score.
Do not include markdown — JSON only.
"""


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _genre_from_hint(hint: str) -> Genre:
    try:
        return Genre(hint)
    except ValueError:
        return Genre.SHOOTER


def fallback_gamespec(prompt: str, answers: dict[str, str]) -> GameSpec:
    hint = infer_genre_hint(prompt)
    genre = _genre_from_hint(hint)
    twist = answers.get("twist") or "a distinctive mechanic from clarify answers"
    win = answers.get("win") or "clear the objective"
    art = answers.get("art") or "minimal geometric"
    difficulty = answers.get("difficulty") or "standard"
    title = {
        Genre.SHOOTER: "Orbit Run",
        Genre.RUNNER: "Lane Rush",
        Genre.PUZZLE: "Tile Lock",
    }[genre]
    return GameSpec(
        genre=genre,
        title=title,
        twist=twist,
        prompt=prompt,
        controls=ControlScheme(move="arrows", action="space", notes=f"difficulty={difficulty}"),
        entities=[
            EntitySpec(id="player", role="player", behavior="avatar", count=1),
            EntitySpec(id="foe", role="enemy", behavior="threat", count=6),
        ],
        win_lose=WinLoseSpec(win=win, lose="player is defeated"),
        scoring=ScoringSpec(events=["progress +10", "threat cleared +100"]),
        visual=VisualSpec(
            palette=["#07141a", "#f0a202", "#3ecf8e"],
            art_vibe=art,
        ),
        acceptance=[
            "game boots",
            "player can move",
            "player can act",
            "enemy or obstacle exists",
            "score updates",
            "win or lose reachable",
        ],
    )


def parse_gamespec_response(
    raw: str,
    *,
    prompt: str,
    answers: dict[str, str],
) -> GameSpec:
    data = _extract_json_object(raw)
    if not data:
        raise ValueError("lock_spec response is not JSON")
    data.setdefault("prompt", prompt)
    if answers.get("twist"):
        data["twist"] = answers["twist"]
    if answers.get("win") and isinstance(data.get("win_lose"), dict):
        data["win_lose"] = {**data["win_lose"], "win": answers["win"]}
    if answers.get("art") and isinstance(data.get("visual"), dict):
        data["visual"] = {**data["visual"], "art_vibe": answers["art"]}
    return GameSpec.model_validate(data)


def build_gamespec(
    prompt: str,
    answers: dict[str, str] | None = None,
    *,
    client: LLMClient | None = None,
) -> tuple[GameSpec, str]:
    """Return (GameSpec, source) where source is 'llm' or 'fallback'."""
    answers = answers or {}
    llm = client or get_llm_client()
    answer_lines = "\n".join(f"- {k}: {v}" for k, v in answers.items()) or "(none)"
    user = (
        f"Player prompt:\n{prompt.strip()}\n\n"
        f"Clarifying answers:\n{answer_lines}\n\n"
        "Lock the GameSpec JSON now."
    )
    try:
        raw = llm.complete(LOCK_SYSTEM, user)
        return parse_gamespec_response(raw, prompt=prompt, answers=answers), "llm"
    except Exception:
        return fallback_gamespec(prompt, answers), "fallback"


def gamespec_path(run_id: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.artifacts_dir) / run_id / "gamespec.json"


def write_gamespec(
    run_id: str,
    spec: GameSpec,
    settings: Settings | None = None,
) -> Path:
    path = gamespec_path(run_id, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    return path


def lock_gamespec(
    prompt: str,
    run_id: str,
    answers: dict[str, str] | None = None,
    *,
    client: LLMClient | None = None,
    settings: Settings | None = None,
) -> tuple[GameSpec, Path, str]:
    """Build, validate, and persist GameSpec. Returns (spec, path, source)."""
    spec, source = build_gamespec(prompt, answers, client=client)
    path = write_gamespec(run_id, spec, settings=settings)
    return spec, path, source
