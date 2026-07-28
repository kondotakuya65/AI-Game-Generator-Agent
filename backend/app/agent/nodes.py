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
    from langgraph.types import interrupt

    from app.agent.resume import parse_clarify_resume

    prompt = state.get("prompt") or ""
    existing = dict(state.get("answers") or {})
    questions, source = ask_clarify_questions(prompt)
    payload = [q.model_dump() for q in questions]

    base_trace = (
        _trace(
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
        )
    )

    if existing:
        return {
            "status": "clarifying",
            "clarify_round": int(state.get("clarify_round") or 0) + 1,
            "questions": payload,
            "answers": existing,
            "messages": [
                f"clarify: asked {len(payload)} via {source}; answers pre-filled (no pause)"
            ],
            "trace": base_trace
            + _trace(
                "clarify",
                "Answers already present — skip human pause.",
                kind="observation",
                data={"answer_keys": list(existing.keys())},
            ),
        }

    resume_raw = interrupt(
        {
            "type": "clarify",
            "prompt": "Answer uniqueness questions, then confirm to lock GameSpec.",
            "actions": ["confirm"],
            "questions": payload,
            "game_prompt": prompt,
        }
    )
    resume = parse_clarify_resume(resume_raw)
    answers = resume.answers
    return {
        "status": "clarifying",
        "clarify_round": int(state.get("clarify_round") or 0) + 1,
        "questions": payload,
        "answers": answers,
        "messages": [
            f"clarify: asked {len(payload)} via {source}; locked answers for {len(answers)} keys"
        ],
        "trace": base_trace
        + _trace(
            "clarify",
            f"Human confirmed {len(answers)} answer(s).",
            kind="observation",
            data={"answer_keys": list(answers.keys())},
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
    from app.agent.design import design_from_gamespec

    run_id = state.get("run_id") or "local"
    gamespec = state.get("gamespec")
    if not gamespec:
        return {
            "status": "failed",
            "error": "design requires locked gamespec",
            "messages": ["design: missing gamespec"],
            "trace": _trace(
                "design",
                "Cannot design without GameSpec.",
                kind="observation",
            ),
        }

    plan, paths, source = design_from_gamespec(gamespec, run_id)
    design = plan.model_dump(mode="json")
    acceptance = [it.model_dump(mode="json") for it in plan.acceptance_tests]
    return {
        "status": "designing",
        "design": design,
        "acceptance_tests": acceptance,
        "messages": [
            f"design: wrote plan via {source}; {len(acceptance)} acceptance items"
        ],
        "trace": _trace(
            "design",
            "Produce mechanics, assets, and acceptance checklist from GameSpec.",
            kind="thought",
            data={"source": source},
        )
        + _trace(
            "design",
            "write_design_plan",
            kind="action",
            data=paths,
        )
        + _trace(
            "design",
            f"Design ready ({source}): {len(acceptance)} acceptance items.",
            kind="observation",
            data={
                "acceptance_ids": [it["id"] for it in acceptance],
                "asset_plan_len": len(plan.asset_plan),
            },
        ),
    }


def code_node(state: GameBuilderState) -> dict[str, Any]:
    from app.agent.code import code_from_gamespec

    run_id = state.get("run_id") or "local"
    gamespec = state.get("gamespec")
    if not gamespec:
        return {
            "status": "failed",
            "error": "code requires locked gamespec",
            "messages": ["code: missing gamespec"],
            "trace": _trace(
                "code",
                "Cannot code without GameSpec.",
                kind="observation",
            ),
        }

    root, filenames, source = code_from_gamespec(gamespec, run_id)
    artifact_dir = str(root)
    return {
        "status": "coding",
        "artifact_dir": artifact_dir,
        "messages": [f"code: wrote {len(filenames)} files via {source}"],
        "trace": _trace(
            "code",
            "Render genre template and write HTML/Canvas/JS files.",
            kind="thought",
            data={"source": source, "genre": gamespec.get("genre")},
        )
        + _trace(
            "code",
            "write_game_files",
            kind="action",
            data={"dir": artifact_dir, "files": filenames},
        )
        + _trace(
            "code",
            f"Wrote {', '.join(filenames)} under {artifact_dir}.",
            kind="observation",
        ),
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
