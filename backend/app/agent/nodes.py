"""Game builder graph nodes — stubs for skeleton walk (real logic in later PRs)."""

from __future__ import annotations

from typing import Any, Literal

from app.agent.state import GameBuilderState, TraceEvent


def _trace(
    node: str,
    message: str,
    *,
    kind: str = "status",
    data: dict[str, Any] | None = None,
) -> list[TraceEvent]:
    event: TraceEvent = {"kind": kind, "node": node, "message": message}  # type: ignore[typeddict-item]
    if data:
        event["data"] = data
    return [event]


def clarify_node(state: GameBuilderState) -> dict[str, Any]:
    prompt = state.get("prompt") or ""
    questions = [
        {
            "id": "twist",
            "text": "What unique twist should set this game apart?",
            "options": ["near-miss shields", "gravity wells", "sideways only"],
        }
    ]
    return {
        "status": "clarifying",
        "clarify_round": int(state.get("clarify_round") or 0) + 1,
        "questions": questions,
        "messages": [f"clarify: asked {len(questions)} question(s) for {prompt[:48]!r}"],
        "trace": _trace(
            "clarify",
            "Stub: ask uniqueness questions before locking GameSpec.",
            kind="thought",
            data={"question_count": len(questions)},
        )
        + _trace(
            "clarify",
            "emit_clarify_questions",
            kind="action",
            data={"questions": questions},
        )
        + _trace(
            "clarify",
            "Stub questions ready (answers may already be pre-filled).",
            kind="observation",
        ),
    }


def lock_spec_node(state: GameBuilderState) -> dict[str, Any]:
    prompt = state.get("prompt") or "game"
    answers = state.get("answers") or {}
    twist = answers.get("twist") or "shields recharge on near-miss"
    gamespec = {
        "genre": "shooter",
        "title": "Orbit Run",
        "twist": twist,
        "prompt": prompt,
        "controls": {"move": "arrows", "action": "space", "notes": ""},
        "entities": [{"id": "player", "role": "player", "behavior": "ship", "count": 1}],
        "win_lose": {"win": "clear 5 waves", "lose": "hull reaches 0"},
        "scoring": {"events": ["enemy destroyed +100"], "win_score": None},
        "visual": {
            "palette": ["#07141a", "#f0a202", "#3ecf8e"],
            "art_vibe": "minimal geometric",
            "notes": "",
        },
        "acceptance": [
            "game boots",
            "player can move",
            "score updates",
        ],
    }
    return {
        "status": "spec_locked",
        "gamespec": gamespec,
        "spec_locked": True,
        "messages": ["lock_spec: GameSpec locked (stub)"],
        "trace": _trace(
            "lock_spec",
            "Stub: lock GameSpec from prompt + answers.",
            kind="thought",
        )
        + _trace(
            "lock_spec",
            "write_gamespec",
            kind="action",
            data={"title": gamespec["title"]},
        )
        + _trace(
            "lock_spec",
            f"Locked {gamespec['title']!r} ({gamespec['genre']}).",
            kind="observation",
        ),
    }


def design_node(state: GameBuilderState) -> dict[str, Any]:
    acceptance = [
        {"id": "boots", "description": "game boots", "passed": None},
        {"id": "move", "description": "player can move", "passed": None},
        {"id": "score", "description": "score updates", "passed": None},
    ]
    design = {
        "mechanics": "Stub mechanics plan from GameSpec.",
        "asset_plan": "Canvas shapes only.",
        "acceptance_tests": acceptance,
    }
    return {
        "status": "designing",
        "design": design,
        "acceptance_tests": acceptance,
        "messages": ["design: stub plan + acceptance seeds"],
        "trace": _trace("design", "Stub: produce mechanics + acceptance.", kind="thought")
        + _trace("design", "write_design_plan", kind="action")
        + _trace(
            "design",
            f"Acceptance items: {len(acceptance)}.",
            kind="observation",
        ),
    }


def code_node(state: GameBuilderState) -> dict[str, Any]:
    run_id = state.get("run_id") or "local"
    artifact_dir = f"artifacts/{run_id}/game"
    return {
        "status": "coding",
        "artifact_dir": artifact_dir,
        "messages": [f"code: stub artifact at {artifact_dir}"],
        "trace": _trace("code", "Stub: write HTML/Canvas/JS files.", kind="thought")
        + _trace("code", "write_game_files", kind="action", data={"dir": artifact_dir})
        + _trace("code", "Stub files marked ready (no disk write yet).", kind="observation"),
    }


def test_node(state: GameBuilderState) -> dict[str, Any]:
    """Stub always passes so the happy path reaches deploy without repair."""
    report = {
        "passed": True,
        "items": [{"id": "boots", "description": "game boots", "passed": True}],
        "summary": "Stub tests passed.",
    }
    return {
        "status": "testing",
        "test_report": report,
        "test_passed": True,
        "messages": ["test: stub pass"],
        "trace": _trace("test", "Stub: run acceptance checks.", kind="thought")
        + _trace("test", "run_acceptance", kind="action")
        + _trace("test", "All stub checks passed.", kind="observation", data=report),
    }


def repair_node(state: GameBuilderState) -> dict[str, Any]:
    count = int(state.get("repair_count") or 0) + 1
    return {
        "status": "repairing",
        "repair_count": count,
        "messages": [f"repair: stub attempt {count}"],
        "trace": _trace(
            "repair",
            f"Stub: patch artifact (attempt {count}).",
            kind="thought",
        )
        + _trace("repair", "patch_game_files", kind="action")
        + _trace("repair", "Stub patch applied.", kind="observation"),
    }


def deploy_node(state: GameBuilderState) -> dict[str, Any]:
    run_id = state.get("run_id") or "local"
    play_url = f"/play/{run_id}"
    return {
        "status": "completed",
        "play_url": play_url,
        "summary": f"Stub deploy ready at {play_url}",
        "messages": [f"deploy: {play_url}"],
        "trace": _trace("deploy", "Stub: serve static play URL.", kind="thought")
        + _trace("deploy", "mount_play_url", kind="action", data={"play_url": play_url})
        + _trace("deploy", f"Playable at {play_url}.", kind="observation"),
    }


def route_after_test(
    state: GameBuilderState,
) -> Literal["deploy", "repair", "failed"]:
    """Conditional edge placeholder: fail → repair while budget remains."""
    passed = state.get("test_passed")
    if passed:
        return "deploy"
    repair_count = int(state.get("repair_count") or 0)
    budget = int(state.get("repair_budget") or 0)
    if repair_count < budget:
        return "repair"
    return "failed"
