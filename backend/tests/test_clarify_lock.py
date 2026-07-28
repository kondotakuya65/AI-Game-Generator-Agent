"""Clarify / lock_spec JSON + answer-merge tests."""

from __future__ import annotations

import json

from app.agent.clarify import ask_clarify_questions, parse_clarify_response
from app.agent.json_util import extract_json_object
from app.agent.lock_spec import apply_answers_to_data, build_gamespec, parse_gamespec_response
from app.llm.provider import MockLLMClient


class BrokenJSONClient:
    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        return "Sure! Here are some thoughts about your game without JSON."


class CustomIdClarifyClient:
    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        return json.dumps(
            {
                "questions": [
                    {
                        "id": "unique_hook",
                        "text": "Hook?",
                        "options": ["a", "b"],
                    },
                    {
                        "id": "victory_rule",
                        "text": "Win how?",
                        "options": ["x", "y"],
                    },
                    {
                        "id": "look_feel",
                        "text": "Look?",
                        "options": ["neon", "pixel"],
                    },
                ]
            }
        )


def test_extract_json_object_from_fenced_prose():
    raw = 'Intro\n```json\n{"questions":[{"id":"a","text":"A?","options":["1","2"]}]}\n```\nThanks'
    data = extract_json_object(raw)
    assert data is not None
    assert "questions" in data


def test_parse_clarify_tolerates_trailing_text():
    raw = (
        '{"questions":['
        '{"id":"twist","text":"Twist?","options":["a","b"]},'
        '{"id":"win","text":"Win?","options":["c","d"]},'
        '{"id":"art","text":"Art?","options":["e","f"]}'
        "]}\nI hope that helps!"
    )
    qs = parse_clarify_response(raw)
    assert len(qs) == 3
    assert qs[0].id == "twist"


def test_ask_clarify_falls_back_with_reason():
    qs, source = ask_clarify_questions("space shooter", client=BrokenJSONClient())
    assert len(qs) >= 3
    assert source.startswith("fallback:")


def test_ask_clarify_mock_is_llm_source():
    qs, source = ask_clarify_questions("space shooter", client=MockLLMClient())
    assert source == "llm"
    assert qs[0].text.startswith("What twist makes")


def test_parse_clarify_pads_missing_options():
    raw = json.dumps(
        {
            "questions": [
                {"id": "twist", "text": "What twist?", "options": []},
                {"id": "win", "text": "How to win?"},
                {"id": "art", "text": "Art vibe?", "options": ["neon only"]},
            ]
        }
    )
    qs = parse_clarify_response(raw)
    assert all(len(q.options) >= 2 for q in qs)
    assert "neon only" in qs[2].options


def test_apply_answers_maps_custom_ids():
    data = apply_answers_to_data(
        {
            "genre": "shooter",
            "title": "X",
            "twist": "placeholder",
            "prompt": "p",
            "controls": {"move": "arrows", "action": "space"},
            "entities": [{"id": "player", "role": "player"}],
            "win_lose": {"win": "old", "lose": "dead"},
            "scoring": {"events": ["hit +1"]},
            "visual": {"palette": ["#000"], "art_vibe": "plain"},
            "acceptance": ["boots"],
        },
        {
            "unique_hook": "gravity wells",
            "victory_rule": "clear 5 waves",
            "look_feel": "neon vectors",
        },
        "p",
    )
    assert data["twist"] == "gravity wells"
    assert data["win_lose"]["win"] == "clear 5 waves"
    assert data["visual"]["art_vibe"] == "neon vectors"


def test_build_gamespec_merges_answers_over_llm():
    answers = {
        "twist": "only sideways movement",
        "win": "survive 60s",
        "art": "retro pixel",
    }
    spec, source = build_gamespec(
        "Make a space shooter",
        answers,
        client=MockLLMClient(),
    )
    assert source == "llm"
    assert spec.twist == "only sideways movement"
    assert spec.win_lose.win == "survive 60s"
    assert spec.visual.art_vibe == "retro pixel"


def test_parse_gamespec_with_prose_wrapper():
    pure = MockLLMClient().complete("Lock GameSpec JSON", "space")
    wrapped = f"Sure!\n{pure}\nbye"
    spec = parse_gamespec_response(
        wrapped,
        prompt="space",
        answers={"twist": "custom twist"},
    )
    assert spec.twist == "custom twist"


def test_parse_gamespec_coerces_messy_ollama_genre():
    messy = {
        "genre": "Space Shooter Arcade",
        "title": "Nebula Dash",
        "twist": "gravity wells",
        "prompt": "Make a space shooter",
        "controls": {"move": "wasd"},
        "entities": [{"id": "ship", "role": "hero"}],
        "win_lose": "survive 60 seconds",
        "scoring": {"events": "kill +10", "win_score": "100"},
        "visual": {"art_vibe": "neon"},
        "acceptance": ["boots"],
    }
    spec = parse_gamespec_response(
        json.dumps(messy),
        prompt="Make a space shooter",
        answers={"win": "clear 5 waves", "art": "retro pixel"},
    )
    assert spec.genre.value == "shooter"
    assert spec.title == "Nebula Dash"
    assert any(e.role == "player" for e in spec.entities)
    assert spec.win_lose.win == "clear 5 waves"
    assert spec.visual.art_vibe == "retro pixel"
