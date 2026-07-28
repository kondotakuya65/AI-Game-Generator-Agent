"""HTTP API for game builder runs (clarify → confirm lock)."""

from __future__ import annotations

from fastapi import APIRouter
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


@router.post("")
def create_run(body: CreateRunRequest) -> dict:
    return service.create_run(body.prompt)


@router.get("")
def list_runs(limit: int = 20) -> dict:
    return {"runs": service.list_runs(limit=limit)}


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    return service.get_run(run_id)


@router.post("/{run_id}/confirm")
def confirm_run(run_id: str, body: ConfirmRunRequest) -> dict:
    return service.confirm_run(run_id, body.answers)
