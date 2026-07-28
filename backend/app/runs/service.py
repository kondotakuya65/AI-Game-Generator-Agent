"""In-memory game builder run orchestration (LangGraph thread_id = run_id)."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import HTTPException

from app.agent.graph import clear_graph_cache, get_compiled_graph
from app.agent.resume import resume_with_answers
from app.agent.state import initial_state
from app.config import get_settings

RunStatus = Literal["awaiting_clarify", "completed", "failed"]


@dataclass
class RunRecord:
    run_id: str
    prompt: str
    status: RunStatus
    created_at: str
    updated_at: str
    error: str | None = None
    summary: str | None = None


_lock = threading.Lock()
_runs: dict[str, RunRecord] = {}


def clear_runs() -> None:
    with _lock:
        _runs.clear()
    clear_graph_cache()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _config(run_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": run_id}}


def _interrupt_from_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not result:
        return None
    items = result.get("__interrupt__") or []
    if not items:
        return None
    first = items[0]
    value = getattr(first, "value", first)
    return value if isinstance(value, dict) else {"value": value}


def _public_state(values: dict[str, Any] | None) -> dict[str, Any]:
    if not values:
        return {}
    keep = {
        "run_id",
        "prompt",
        "clarify_round",
        "questions",
        "answers",
        "gamespec",
        "spec_locked",
        "design",
        "acceptance_tests",
        "artifact_dir",
        "test_report",
        "test_passed",
        "repair_count",
        "repair_budget",
        "play_url",
        "status",
        "error",
        "summary",
        "messages",
        "trace",
    }
    return {k: values.get(k) for k in keep if k in values}


def _snapshot(run: RunRecord) -> dict[str, Any]:
    graph = get_compiled_graph()
    snap = graph.get_state(_config(run.run_id))
    values = dict(snap.values or {})
    interrupt = None
    tasks = getattr(snap, "tasks", None) or ()
    for task in tasks:
        interrupts = getattr(task, "interrupts", None) or ()
        if interrupts:
            val = getattr(interrupts[0], "value", interrupts[0])
            interrupt = val if isinstance(val, dict) else {"value": val}
            break

    status = run.status
    if interrupt and status != "failed":
        status = "awaiting_clarify"
    elif not interrupt and status == "awaiting_clarify":
        if values.get("spec_locked") or values.get("play_url") or values.get("summary"):
            status = "completed"

    return {
        "run_id": run.run_id,
        "prompt": run.prompt,
        "status": status,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "error": run.error or values.get("error"),
        "summary": values.get("summary") or run.summary,
        "interrupt": interrupt,
        "state": _public_state(values),
    }


def create_run(prompt: str) -> dict[str, Any]:
    prompt = (prompt or "").strip()
    if len(prompt) < 3:
        raise HTTPException(status_code=400, detail="prompt must be at least 3 characters")

    run_id = str(uuid.uuid4())
    now = _now()
    settings = get_settings()
    record = RunRecord(
        run_id=run_id,
        prompt=prompt,
        status="awaiting_clarify",
        created_at=now,
        updated_at=now,
    )
    with _lock:
        _runs[run_id] = record

    graph = get_compiled_graph()
    try:
        result = graph.invoke(
            initial_state(
                prompt,
                run_id=run_id,
                repair_budget=settings.repair_budget,
            ),
            config=_config(run_id),
        )
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)
        record.updated_at = _now()
        raise HTTPException(status_code=500, detail=f"run failed: {exc}") from exc

    interrupt = _interrupt_from_result(result if isinstance(result, dict) else None)
    record.updated_at = _now()
    if interrupt:
        record.status = "awaiting_clarify"
    else:
        record.status = "completed"
        if isinstance(result, dict):
            record.summary = result.get("summary")
    return _snapshot(record)


def get_run(run_id: str) -> dict[str, Any]:
    with _lock:
        record = _runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")
    return _snapshot(record)


def confirm_run(run_id: str, answers: dict[str, str]) -> dict[str, Any]:
    with _lock:
        record = _runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")

    current = _snapshot(record)
    if current["status"] == "completed":
        raise HTTPException(status_code=409, detail="run already completed")
    if current["status"] == "failed":
        raise HTTPException(status_code=409, detail="run failed; start a new run")
    if not current.get("interrupt"):
        raise HTTPException(status_code=409, detail="run is not awaiting clarify answers")

    cleaned = {str(k): str(v).strip() for k, v in answers.items() if str(v).strip()}
    if not cleaned:
        raise HTTPException(status_code=400, detail="answers must not be empty")

    graph = get_compiled_graph()
    try:
        result = graph.invoke(
            resume_with_answers(cleaned),
            config=_config(run_id),
        )
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)
        record.updated_at = _now()
        raise HTTPException(status_code=500, detail=f"confirm failed: {exc}") from exc

    interrupt = _interrupt_from_result(result if isinstance(result, dict) else None)
    record.updated_at = _now()
    if interrupt:
        record.status = "awaiting_clarify"
    else:
        record.status = "completed"
        if isinstance(result, dict):
            record.summary = result.get("summary")
    return _snapshot(record)


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        items = sorted(_runs.values(), key=lambda r: r.created_at, reverse=True)[:limit]
    return [
        {
            "run_id": r.run_id,
            "prompt": r.prompt,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in items
    ]


def _sse_events_from_stream(run_id: str, chunks):
    """Yield public event dicts from LangGraph updates stream."""
    for chunk in chunks:
        mode = "updates"
        data = chunk
        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, data = chunk

        if mode == "custom" and isinstance(data, dict):
            yield {
                "type": "progress",
                "run_id": run_id,
                "message": data.get("message") or data.get("phase") or "working…",
                "node": data.get("node"),
                "phase": data.get("phase"),
                "data": data.get("data"),
            }
            continue

        if not isinstance(data, dict):
            continue
        if "__interrupt__" in data:
            raw = data["__interrupt__"]
            items = raw if isinstance(raw, (list, tuple)) else [raw]
            value = None
            if items:
                first = items[0]
                value = getattr(first, "value", first)
            interrupt = value if isinstance(value, dict) else {"value": value}
            yield {
                "type": "interrupt",
                "run_id": run_id,
                "interrupt": interrupt,
            }
            continue
        for node_name, update in data.items():
            if not isinstance(update, dict):
                continue
            yield {"type": "node", "run_id": run_id, "node": node_name}
            for te in update.get("trace") or []:
                yield {
                    "type": "trace",
                    "run_id": run_id,
                    "kind": te.get("kind"),
                    "node": te.get("node") or node_name,
                    "message": te.get("message"),
                    "data": te.get("data"),
                }


def iter_create_run_events(prompt: str):
    """Create a run while yielding SSE-ready event dicts (pause at clarify)."""
    prompt = (prompt or "").strip()
    if len(prompt) < 3:
        raise HTTPException(status_code=400, detail="prompt must be at least 3 characters")

    run_id = str(uuid.uuid4())
    now = _now()
    settings = get_settings()
    record = RunRecord(
        run_id=run_id,
        prompt=prompt,
        status="awaiting_clarify",
        created_at=now,
        updated_at=now,
    )
    with _lock:
        _runs[run_id] = record

    yield {"type": "status", "run_id": run_id, "status": "running", "prompt": prompt}

    graph = get_compiled_graph()
    saw_interrupt = False
    try:
        chunks = graph.stream(
            initial_state(
                prompt,
                run_id=run_id,
                repair_budget=settings.repair_budget,
            ),
            config=_config(run_id),
            stream_mode=["updates", "custom"],
        )
        for event in _sse_events_from_stream(run_id, chunks):
            if event.get("type") == "interrupt":
                saw_interrupt = True
            yield event
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)
        record.updated_at = _now()
        yield {"type": "error", "run_id": run_id, "error": str(exc)}
        return

    record.updated_at = _now()
    snap = _snapshot(record)
    if saw_interrupt or snap.get("interrupt"):
        record.status = "awaiting_clarify"
    else:
        record.status = "completed"
        record.summary = snap.get("summary")
    snap = _snapshot(record)
    yield {"type": "done", **snap}


def iter_confirm_run_events(run_id: str, answers: dict[str, str]):
    """Confirm clarify answers and stream the autonomous pipeline."""
    with _lock:
        record = _runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")

    current = _snapshot(record)
    if current["status"] == "completed":
        raise HTTPException(status_code=409, detail="run already completed")
    if current["status"] == "failed":
        raise HTTPException(status_code=409, detail="run failed; start a new run")
    if not current.get("interrupt"):
        raise HTTPException(status_code=409, detail="run is not awaiting clarify answers")

    cleaned = {str(k): str(v).strip() for k, v in answers.items() if str(v).strip()}
    if not cleaned:
        raise HTTPException(status_code=400, detail="answers must not be empty")

    yield {"type": "status", "run_id": run_id, "status": "running"}

    graph = get_compiled_graph()
    try:
        chunks = graph.stream(
            resume_with_answers(cleaned),
            config=_config(run_id),
            stream_mode=["updates", "custom"],
        )
        for event in _sse_events_from_stream(run_id, chunks):
            yield event
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)
        record.updated_at = _now()
        yield {"type": "error", "run_id": run_id, "error": str(exc)}
        return

    record.updated_at = _now()
    record.status = "completed"
    snap = _snapshot(record)
    record.summary = snap.get("summary")
    snap = _snapshot(record)
    yield {"type": "done", **snap}


def iter_replay_run_events(run_id: str):
    """Replay stored traces for an existing run (UI reconnect)."""
    with _lock:
        record = _runs.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="run not found")

    snap = _snapshot(record)
    yield {"type": "status", "run_id": run_id, "status": snap["status"], "replay": True}
    for te in (snap.get("state") or {}).get("trace") or []:
        yield {
            "type": "trace",
            "run_id": run_id,
            "kind": te.get("kind"),
            "node": te.get("node"),
            "message": te.get("message"),
            "data": te.get("data"),
            "replay": True,
        }
    if snap.get("interrupt"):
        yield {
            "type": "interrupt",
            "run_id": run_id,
            "interrupt": snap["interrupt"],
            "replay": True,
        }
    yield {"type": "done", **snap, "replay": True}
