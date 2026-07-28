"""Game builder graph nodes — clarify is live; later nodes still stubbed."""

from __future__ import annotations

from typing import Any, Literal

from app.agent.clarify import ask_clarify_questions
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
    questions, source = ask_clarify_questions(prompt)
    payload = [q.model_dump() for q in questions]
    return {
        "status": "clarifying",
        "clarify_round": int(state.get("clarify_round") or 0) + 1,
        "questions": payload,
        "messages": [
            f"clarify: asked {len(payload)} question(s) via {source} for {prompt[:48]!r}"
        ],
        "trace": _trace(
            "clarify",
            "Ask 3–5 uniqueness questions before locking GameSpec.",
            kind="thought",
            data={"question_count": len(payload), "source": source},
        )
        + _trace(
            "clarify",
            "emit_clarify_questions",
            kind="action",
            data={"questions": payload, "source": source},
        )
        + _trace(
            "clarify",
            f"{len(payload)} questions ready ({source}).",
            kind="observation",
            data={"ids": [q["id"] for q in payload]},
        ),
    }


def lock_spec_node(state: GameBuilderState) -> dict[str, Any]:
    from app.agent.lock_spec import lock_gamespec

    prompt = state.get("prompt") or "game"
    run_id = state.get("run_id") or "local"
    answers = dict(state.get("answers") or {})
    spec, path, source = lock_gamespec(prompt, run_id, answers)
    gamespec = spec.model_dump(mode="json")
    return {
        "status": "spec_locked",
        "gamespec": gamespec,
        "spec_locked": True,
        "artifact_dir": str(path.parent),
        "messages": [f"lock_spec: wrote {path.name} via {source}"],
        "trace": _trace(
            "lock_spec",
            "Lock GameSpec from prompt + clarifying answers.",
            kind="thought",
            data={"source": source},
        )
        + _trace(
            "lock_spec",
            "write_gamespec",
            kind="action",
            data={"path": str(path), "title": gamespec["title"]},
        )
        + _trace(
            "lock_spec",
            f"Locked {gamespec['title']!r} ({gamespec['genre']}) → {path}.",
            kind="observation",
            data={"acceptance": gamespec.get("acceptance", [])},
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
