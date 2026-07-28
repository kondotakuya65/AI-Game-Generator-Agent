"""Clarifier: ask 3–5 uniqueness questions from the user prompt."""

from __future__ import annotations

import re
from typing import Any

from app.agent.json_util import extract_json_object
from app.llm.provider import LLMClient, get_llm_client
from app.models import ClarifyQuestion

CLARIFY_SYSTEM = """You help design unique HTML5 Canvas games.
Given a player prompt, ask 3 to 5 short uniqueness questions.
Return ONLY valid JSON (no markdown) with this exact shape:
{"questions":[{"id":"snake_case","text":"...","options":["a","b","c"]}]}
Rules:
- ids must be snake_case like twist, difficulty, win, art when possible
- EVERY question MUST include 2-4 short, concrete options (never empty)
- cover twist, difficulty/pacing, win condition, and art vibe
- do not lock a GameSpec — questions only
"""

# Used when the model omits choices so the Studio always has clickable answers.
_DEFAULT_OPTIONS_BY_HINT: dict[str, list[str]] = {
    "twist": [
        "near-miss recharges shields",
        "gravity wells pull shots",
        "only sideways movement",
    ],
    "difficulty": ["casual", "standard", "hard"],
    "win": ["survive 60s", "clear 5 waves", "defeat boss"],
    "art": ["neon vectors", "minimal geometric", "retro pixel"],
    "generic": ["option A", "option B", "option C"],
}


def _default_options_for(qid: str, text: str) -> list[str]:
    blob = f"{qid} {text}".lower()
    if any(k in blob for k in ("twist", "unique", "mechanic", "special", "hook")):
        return list(_DEFAULT_OPTIONS_BY_HINT["twist"])
    if any(k in blob for k in ("difficult", "pace", "hard", "level")):
        return list(_DEFAULT_OPTIONS_BY_HINT["difficulty"])
    if any(k in blob for k in ("win", "goal", "victory", "objective")):
        return list(_DEFAULT_OPTIONS_BY_HINT["win"])
    if any(k in blob for k in ("art", "vibe", "style", "look", "visual")):
        return list(_DEFAULT_OPTIONS_BY_HINT["art"])
    return list(_DEFAULT_OPTIONS_BY_HINT["generic"])


def ensure_question_options(qid: str, text: str, options: list[str]) -> list[str]:
    """Guarantee 2–4 clickable choices for the Studio UI."""
    cleaned = [str(o).strip() for o in options if str(o).strip()]
    # de-dupe preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for o in cleaned:
        key = o.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(o)
    if len(unique) >= 2:
        return unique[:4]
    for o in _default_options_for(qid, text):
        key = o.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(o)
        if len(unique) >= 3:
            break
    return unique[:4]

_FALLBACK_BY_HINT: dict[str, list[dict[str, Any]]] = {
    "shooter": [
        {
            "id": "twist",
            "text": "What unique twist should set this shooter apart?",
            "options": [
                "near-miss recharges shields",
                "gravity wells pull shots",
                "only sideways movement",
            ],
        },
        {
            "id": "difficulty",
            "text": "Target difficulty?",
            "options": ["casual", "standard", "hard"],
        },
        {
            "id": "win",
            "text": "How does the player win?",
            "options": ["survive 60s", "clear 5 waves", "defeat boss"],
        },
        {
            "id": "art",
            "text": "Art vibe?",
            "options": ["neon vectors", "minimal geometric", "retro pixel"],
        },
    ],
    "runner": [
        {
            "id": "twist",
            "text": "What unique twist should set this runner apart?",
            "options": ["lanes shift mid-run", "gravity flips", "collectors steal score"],
        },
        {
            "id": "difficulty",
            "text": "Target difficulty?",
            "options": ["casual", "standard", "hard"],
        },
        {
            "id": "win",
            "text": "How does the player win?",
            "options": ["survive 60s", "reach distance goal", "beat high score once"],
        },
        {
            "id": "art",
            "text": "Art vibe?",
            "options": ["neon vectors", "minimal geometric", "retro pixel"],
        },
    ],
    "puzzle": [
        {
            "id": "twist",
            "text": "What unique twist should set this puzzle apart?",
            "options": ["timed merges", "limited undos", "gravity tiles"],
        },
        {
            "id": "difficulty",
            "text": "Target difficulty?",
            "options": ["casual", "standard", "hard"],
        },
        {
            "id": "win",
            "text": "How does the player win?",
            "options": ["clear the board", "reach target score", "solve N levels"],
        },
        {
            "id": "art",
            "text": "Art vibe?",
            "options": ["neon vectors", "minimal geometric", "retro pixel"],
        },
    ],
}


def infer_genre_hint(prompt: str) -> str:
    lower = prompt.lower()
    if any(w in lower for w in ("runner", "endless", "side-scroll", "side scroll")):
        return "runner"
    if any(w in lower for w in ("puzzle", "match", "tetris", "block")):
        return "puzzle"
    if any(w in lower for w in ("shoot", "space", "invader", "bullet", "arcade")):
        return "shooter"
    return "shooter"


def fallback_questions(prompt: str) -> list[ClarifyQuestion]:
    hint = infer_genre_hint(prompt)
    raw = _FALLBACK_BY_HINT.get(hint, _FALLBACK_BY_HINT["shooter"])
    return [ClarifyQuestion.model_validate(q) for q in raw]


def _slug(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return (slug[:40] or fallback)


def parse_clarify_response(raw: str) -> list[ClarifyQuestion]:
    data = extract_json_object(raw)
    if not data:
        raise ValueError("clarify response was not JSON")
    items = data.get("questions")
    if items is None and isinstance(data.get("Questions"), list):
        items = data["Questions"]
    if not isinstance(items, list) or not items:
        raise ValueError("clarify response missing questions list")

    questions: list[ClarifyQuestion] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or item.get("key") or "").strip()
        text = str(item.get("text") or item.get("question") or "").strip()
        if not text:
            continue
        if not qid:
            qid = _slug(text, f"q{i+1}")
        options = item.get("options") or item.get("choices") or []
        if not isinstance(options, list):
            options = []
        options = ensure_question_options(
            qid, text, [str(o) for o in options]
        )
        questions.append(ClarifyQuestion(id=qid, text=text, options=options))

    if not 2 <= len(questions) <= 6:
        raise ValueError(f"expected 2–6 questions, got {len(questions)}")
    return questions[:5]


def ask_clarify_questions(
    prompt: str,
    *,
    client: LLMClient | None = None,
) -> tuple[list[ClarifyQuestion], str]:
    """
    Return (questions, source).
    source is 'llm' or 'fallback:<reason>' when the model output cannot be used.
    """
    llm = client or get_llm_client()
    user = f"Player prompt:\n{prompt.strip()}\n\nAsk uniqueness questions now. JSON only."
    try:
        raw = llm.complete(CLARIFY_SYSTEM, user, json_mode=True)
        if not (raw or "").strip():
            raise ValueError("empty LLM response")
        questions = parse_clarify_response(raw)
        return questions, "llm"
    except Exception as exc:  # noqa: BLE001
        reason = type(exc).__name__
        msg = str(exc).strip().replace(" ", "_")[:48]
        return fallback_questions(prompt), f"fallback:{reason}:{msg}"
