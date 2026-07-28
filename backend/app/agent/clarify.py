"""Clarifier: ask 3–5 uniqueness questions from the user prompt."""

from __future__ import annotations

import json
import re
from typing import Any

from app.llm.provider import LLMClient, get_llm_client
from app.models import ClarifyQuestion

CLARIFY_SYSTEM = """You help design unique HTML5 Canvas games.
Given a player prompt, ask 3 to 5 short uniqueness questions.
Return ONLY valid JSON with this shape:
{"questions":[{"id":"snake_case","text":"...","options":["a","b","c"]}]}
Cover twist, difficulty or pacing, win condition, and art vibe when relevant.
Do not lock a GameSpec yet — questions only.
"""

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


def parse_clarify_response(raw: str) -> list[ClarifyQuestion]:
    data = _extract_json_object(raw)
    if not data or "questions" not in data:
        raise ValueError("clarify response missing questions")
    items = data["questions"]
    if not isinstance(items, list):
        raise ValueError("questions must be a list")
    questions = [ClarifyQuestion.model_validate(q) for q in items]
    if not 3 <= len(questions) <= 5:
        raise ValueError(f"expected 3–5 questions, got {len(questions)}")
    return questions


def ask_clarify_questions(
    prompt: str,
    *,
    client: LLMClient | None = None,
) -> tuple[list[ClarifyQuestion], str]:
    """
    Return (questions, source) where source is 'llm' or 'fallback'.
    Always yields 3–5 validated questions.
    """
    llm = client or get_llm_client()
    user = f"Player prompt:\n{prompt.strip()}\n\nAsk uniqueness questions now."
    try:
        raw = llm.complete(CLARIFY_SYSTEM, user)
        questions = parse_clarify_response(raw)
        return questions, "llm"
    except Exception:
        return fallback_questions(prompt), "fallback"
