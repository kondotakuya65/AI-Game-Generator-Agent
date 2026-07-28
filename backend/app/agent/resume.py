"""Clarify resume helpers (human answers → continue to lock_spec)."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command
from pydantic import BaseModel, Field


class ClarifyResumeInput(BaseModel):
    answers: dict[str, str] = Field(
        ...,
        min_length=1,
        description="Map of question id → chosen answer text",
    )


def parse_clarify_resume(value: Any) -> ClarifyResumeInput:
    if isinstance(value, ClarifyResumeInput):
        return value
    if isinstance(value, dict):
        # Allow {"answers": {...}} or bare answer map
        if "answers" in value:
            return ClarifyResumeInput.model_validate(value)
        return ClarifyResumeInput(answers={str(k): str(v) for k, v in value.items()})
    raise ValueError(f"Unsupported clarify resume payload: {type(value)!r}")


def resume_with_answers(answers: dict[str, str]) -> Command:
    payload = ClarifyResumeInput(answers=answers).model_dump()
    return Command(resume=payload)
