"""HTTP API for game builder runs (clarify → confirm lock) + SSE traces."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.runs import service

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        examples=["Make a new game like a space shooter."],
    )


class ConfirmRunRequest(BaseModel):
    answers: dict[str, str] = Field(
        ...,
        min_length=1,
        description="question id → answer text",
    )


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def _sse_stream(events: Iterator[dict[str, Any]]) -> Iterator[str]:
    yield ": connected\n\n"
    for event in events:
        yield _sse(event)
        yield ": ping\n\n"


@router.post("")
def create_run(body: CreateRunRequest) -> dict:
    return service.create_run(body.prompt)


@router.get("")
def list_runs(limit: int = 20) -> dict:
    return {"runs": service.list_runs(limit=limit)}


@router.post("/stream")
def create_run_stream(body: CreateRunRequest) -> StreamingResponse:
    """Create a run and stream thought/action/observation traces as SSE."""
    return StreamingResponse(
        _sse_stream(service.iter_create_run_events(body.prompt)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/stream")
def replay_run_stream(run_id: str) -> StreamingResponse:
    """Replay stored traces for a run (UI reconnect)."""
    return StreamingResponse(
        _sse_stream(service.iter_replay_run_events(run_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{run_id}/confirm/stream")
def confirm_run_stream(run_id: str, body: ConfirmRunRequest) -> StreamingResponse:
    """Confirm answers and stream the autonomous pipeline as SSE."""
    return StreamingResponse(
        _sse_stream(service.iter_confirm_run_events(run_id, body.answers)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    return service.get_run(run_id)


@router.post("/{run_id}/confirm")
def confirm_run(run_id: str, body: ConfirmRunRequest) -> dict:
    return service.confirm_run(run_id, body.answers)
