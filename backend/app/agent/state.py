"""Typed LangGraph state for the game builder agent."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, NotRequired, TypedDict

# Pipeline node order (happy path). Repair is reached via conditional edge from test.
NODE_ORDER = (
    "clarify",
    "lock_spec",
    "design",
    "code",
    "test",
    "deploy",
)

# Includes repair for stub walks / docs; not always visited on happy path.
ALL_NODES = NODE_ORDER + ("repair",)


class TraceEvent(TypedDict, total=False):
    kind: Literal["thought", "action", "observation", "status"]
    node: str
    message: str
    data: dict[str, Any]


class GameBuilderState(TypedDict):
    """Shared graph state. List fields use append reducers."""

    run_id: str
    prompt: str

    clarify_round: NotRequired[int]
    questions: Annotated[list[dict[str, Any]], operator.add]
    answers: NotRequired[dict[str, str]]

    gamespec: NotRequired[dict[str, Any] | None]
    spec_locked: NotRequired[bool]

    design: NotRequired[dict[str, Any] | None]
    acceptance_tests: Annotated[list[dict[str, Any]], operator.add]

    artifact_dir: NotRequired[str | None]
    test_report: NotRequired[dict[str, Any] | None]
    test_passed: NotRequired[bool | None]

    repair_count: NotRequired[int]
    repair_budget: NotRequired[int]

    play_url: NotRequired[str | None]
    status: NotRequired[str]
    error: NotRequired[str | None]
    summary: NotRequired[str | None]

    messages: Annotated[list[str], operator.add]
    trace: Annotated[list[TraceEvent], operator.add]


def initial_state(
    prompt: str,
    *,
    run_id: str = "local",
    repair_budget: int = 3,
    answers: dict[str, str] | None = None,
) -> GameBuilderState:
    return {
        "run_id": run_id,
        "prompt": prompt,
        "clarify_round": 0,
        "questions": [],
        "answers": answers or {},
        "gamespec": None,
        "spec_locked": False,
        "design": None,
        "acceptance_tests": [],
        "artifact_dir": None,
        "test_report": None,
        "test_passed": None,
        "repair_count": 0,
        "repair_budget": repair_budget,
        "play_url": None,
        "status": "created",
        "error": None,
        "summary": None,
        "messages": [],
        "trace": [],
    }
