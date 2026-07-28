"""Lock a validated GameSpec from prompt + clarify answers; persist JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agent.clarify import infer_genre_hint
from app.agent.json_util import extract_json_object
from app.config import Settings, get_settings
from app.llm.provider import LLMClient, get_llm_client
from app.models import GameSpec, Genre

LOCK_SYSTEM = """You lock a GameSpec JSON for an HTML5 Canvas game.
Return ONLY valid JSON (no markdown) matching this shape closely:
{
  "genre": "shooter",
  "title": "Short Name",
  "twist": "...",
  "prompt": "...",
  "controls": {"move": "arrows", "action": "space", "notes": ""},
  "entities": [{"id": "player", "role": "player", "behavior": "...", "count": 1}],
  "win_lose": {"win": "...", "lose": "..."},
  "scoring": {"events": ["hit +100"], "win_score": null},
  "visual": {"palette": ["#07141a", "#f0a202"], "art_vibe": "...", "notes": ""},
  "acceptance": ["game boots", "player can move", "score updates"]
}
CRITICAL: genre MUST be exactly one of: shooter, runner, puzzle (lowercase, no other words).
You MUST incorporate every clarifying answer into twist / win_lose / visual.art_vibe / controls.notes.
entities must include one role=player. acceptance must list boots, move, score at minimum.
"""


def _genre_from_hint(hint: str) -> Genre:
    try:
        return Genre(hint)
    except ValueError:
        return Genre.SHOOTER


def coerce_genre(value: Any, prompt: str = "") -> str:
    """Map messy LLM genre strings onto shooter|runner|puzzle."""
    if isinstance(value, Genre):
        return value.value
    text = str(value or "").strip().lower()
    if text in {g.value for g in Genre}:
        return text
    blob = f"{text} {prompt}".lower()
    if any(w in blob for w in ("runner", "endless", "side-scroll", "side scroll", "lane")):
        return Genre.RUNNER.value
    if any(w in blob for w in ("puzzle", "match", "tetris", "tile", "block")):
        return Genre.PUZZLE.value
    if any(w in blob for w in ("shoot", "space", "invader", "bullet", "arcade", "blaster")):
        return Genre.SHOOTER.value
    return infer_genre_hint(prompt or text)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def normalize_gamespec_data(data: dict[str, Any], *, prompt: str) -> dict[str, Any]:
    """Repair common Ollama shape mistakes before Pydantic validation."""
    out = dict(data)
    out["genre"] = coerce_genre(out.get("genre"), prompt)
    out["prompt"] = str(out.get("prompt") or prompt).strip() or prompt
    out["title"] = str(out.get("title") or "Untitled Game").strip()[:80] or "Untitled Game"
    out["twist"] = str(out.get("twist") or "a distinctive mechanic").strip() or "a distinctive mechanic"

    controls = _as_dict(out.get("controls"))
    out["controls"] = {
        "move": str(controls.get("move") or "arrows"),
        "action": str(controls.get("action") or "space"),
        "notes": str(controls.get("notes") or ""),
    }

    win_lose = out.get("win_lose")
    if isinstance(win_lose, str) and win_lose.strip():
        win_lose = {"win": win_lose.strip(), "lose": "player is defeated"}
    else:
        win_lose = _as_dict(win_lose)
    out["win_lose"] = {
        "win": str(win_lose.get("win") or "clear the objective").strip() or "clear the objective",
        "lose": str(win_lose.get("lose") or "player is defeated").strip() or "player is defeated",
    }

    scoring = _as_dict(out.get("scoring"))
    win_score = scoring.get("win_score")
    if win_score is not None and not isinstance(win_score, int):
        try:
            win_score = int(win_score)
        except (TypeError, ValueError):
            win_score = None
    out["scoring"] = {
        "events": _as_str_list(scoring.get("events")) or ["progress +10"],
        "win_score": win_score,
    }

    visual = _as_dict(out.get("visual"))
    palette = visual.get("palette")
    if not isinstance(palette, list) or not palette:
        palette = ["#07141a", "#f0a202", "#3ecf8e"]
    out["visual"] = {
        "palette": [str(c) for c in palette if str(c).strip()][:8],
        "art_vibe": str(visual.get("art_vibe") or "minimal geometric").strip()
        or "minimal geometric",
        "notes": str(visual.get("notes") or ""),
    }

    entities_raw = out.get("entities")
    entities: list[dict[str, Any]] = []
    if isinstance(entities_raw, list):
        for i, ent in enumerate(entities_raw):
            if not isinstance(ent, dict):
                continue
            eid = str(ent.get("id") or f"e{i+1}").strip() or f"e{i+1}"
            role = str(ent.get("role") or "enemy").strip().lower() or "enemy"
            count = ent.get("count")
            if count is not None and not isinstance(count, int):
                try:
                    count = int(count)
                except (TypeError, ValueError):
                    count = None
            entities.append(
                {
                    "id": eid,
                    "role": role,
                    "behavior": str(ent.get("behavior") or ""),
                    "count": count,
                }
            )
    if not any(e.get("role") == "player" for e in entities):
        entities.insert(
            0,
            {"id": "player", "role": "player", "behavior": "avatar", "count": 1},
        )
    out["entities"] = entities

    acceptance = _as_str_list(out.get("acceptance"))
    required = ("game boots", "player can move", "score updates")
    lower = {a.lower() for a in acceptance}
    for item in required:
        if not any(item.split()[0] in a for a in lower):
            acceptance.append(item)
    out["acceptance"] = acceptance
    return out


def _answer_by_keywords(answers: dict[str, str], keywords: tuple[str, ...]) -> str | None:
    for key, value in answers.items():
        lk = key.lower()
        if any(k in lk for k in keywords) and value.strip():
            return value.strip()
    return None


def apply_answers_to_data(data: dict[str, Any], answers: dict[str, str], prompt: str) -> dict[str, Any]:
    """Force human answers into GameSpec fields (works for any question ids)."""
    data = dict(data)
    data["prompt"] = prompt

    twist = (
        answers.get("twist")
        or _answer_by_keywords(answers, ("twist", "unique", "mechanic", "special"))
    )
    win = (
        answers.get("win")
        or _answer_by_keywords(answers, ("win", "goal", "objective", "victory"))
    )
    art = (
        answers.get("art")
        or _answer_by_keywords(answers, ("art", "vibe", "style", "visual", "look"))
    )
    difficulty = (
        answers.get("difficulty")
        or _answer_by_keywords(answers, ("difficult", "pace", "hard", "level"))
    )

    if twist:
        data["twist"] = twist
    elif answers and not data.get("twist"):
        # Use first answer as twist so custom ids still affect the game
        data["twist"] = next(iter(answers.values()))

    win_raw = data.get("win_lose")
    if isinstance(win_raw, str) and win_raw.strip():
        win_lose = {"win": win_raw.strip(), "lose": "player is defeated"}
    else:
        win_lose = _as_dict(win_raw)
    if win:
        win_lose["win"] = win
    if not win_lose.get("lose"):
        win_lose["lose"] = "player is defeated"
    data["win_lose"] = win_lose

    visual = _as_dict(data.get("visual"))
    if art:
        visual["art_vibe"] = art
    notes_bits = [f"{k}={v}" for k, v in answers.items()]
    if notes_bits:
        visual["notes"] = "; ".join(notes_bits)
    data["visual"] = visual

    controls = _as_dict(data.get("controls"))
    if difficulty:
        prev = controls.get("notes") or ""
        controls["notes"] = f"difficulty={difficulty}" + (f"; {prev}" if prev else "")
    data["controls"] = controls
    return data


def fallback_gamespec(prompt: str, answers: dict[str, str]) -> GameSpec:
    hint = infer_genre_hint(prompt)
    genre = _genre_from_hint(hint)
    title = {
        Genre.SHOOTER: "Orbit Run",
        Genre.RUNNER: "Lane Rush",
        Genre.PUZZLE: "Tile Lock",
    }[genre]
    raw = {
        "genre": genre.value,
        "title": title,
        "twist": "a distinctive mechanic from clarify answers",
        "prompt": prompt,
        "controls": {"move": "arrows", "action": "space", "notes": ""},
        "entities": [
            {"id": "player", "role": "player", "behavior": "avatar", "count": 1},
            {"id": "foe", "role": "enemy", "behavior": "threat", "count": 6},
        ],
        "win_lose": {"win": "clear the objective", "lose": "player is defeated"},
        "scoring": {"events": ["progress +10", "threat cleared +100"], "win_score": None},
        "visual": {
            "palette": ["#07141a", "#f0a202", "#3ecf8e"],
            "art_vibe": "minimal geometric",
            "notes": "",
        },
        "acceptance": [
            "game boots",
            "player can move",
            "player can act",
            "enemy or obstacle exists",
            "score updates",
            "win or lose reachable",
        ],
    }
    return GameSpec.model_validate(apply_answers_to_data(raw, answers, prompt))


def parse_gamespec_response(
    raw: str,
    *,
    prompt: str,
    answers: dict[str, str],
) -> GameSpec:
    data = extract_json_object(raw)
    if not data:
        raise ValueError("lock_spec response is not JSON")
    data = apply_answers_to_data(data, answers, prompt)
    data = normalize_gamespec_data(data, prompt=prompt)
    return GameSpec.model_validate(data)


def build_gamespec(
    prompt: str,
    answers: dict[str, str] | None = None,
    *,
    client: LLMClient | None = None,
) -> tuple[GameSpec, str]:
    """Return (GameSpec, source) where source is 'llm' or 'fallback:<reason>'."""
    answers = answers or {}
    llm = client or get_llm_client()
    answer_lines = "\n".join(f"- {k}: {v}" for k, v in answers.items()) or "(none)"
    user = (
        f"Player prompt:\n{prompt.strip()}\n\n"
        f"Clarifying answers (must reflect these):\n{answer_lines}\n\n"
        "Lock the GameSpec JSON now. JSON only."
    )
    try:
        raw = llm.complete(LOCK_SYSTEM, user, json_mode=True)
        if not (raw or "").strip():
            raise ValueError("empty LLM response")
        return parse_gamespec_response(raw, prompt=prompt, answers=answers), "llm"
    except Exception as exc:  # noqa: BLE001
        reason = type(exc).__name__
        msg = str(exc).strip().replace(" ", "_")[:48]
        return fallback_gamespec(prompt, answers), f"fallback:{reason}:{msg}"


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
