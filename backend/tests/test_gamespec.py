"""GameSpec / PipelineState validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import (
    EntitySpec,
    GameSpec,
    Genre,
    PipelineState,
    PipelineStatus,
    TraceKind,
    WinLoseSpec,
)


def _valid_spec(**overrides) -> GameSpec:
    base = dict(
        genre=Genre.SHOOTER,
        title="Orbit Run",
        twist="shields recharge on near-miss",
        prompt="Make a space shooter",
        win_lose=WinLoseSpec(win="clear 5 waves", lose="hull=0"),
        entities=[EntitySpec(id="player", role="player")],
        acceptance=["game boots", "player can move"],
    )
    base.update(overrides)
    return GameSpec(**base)


def test_gamespec_valid_roundtrip():
    spec = _valid_spec()
    data = spec.model_dump()
    again = GameSpec.model_validate(data)
    assert again.title == "Orbit Run"
    assert again.genre == Genre.SHOOTER
    assert again.acceptance == ["game boots", "player can move"]


def test_gamespec_rejects_empty_title():
    with pytest.raises(ValidationError):
        _valid_spec(title="")


def test_gamespec_rejects_empty_twist():
    with pytest.raises(ValidationError):
        _valid_spec(twist="")


def test_gamespec_rejects_entities_without_player():
    with pytest.raises(ValidationError, match="player"):
        _valid_spec(
            entities=[EntitySpec(id="drone", role="enemy", behavior="descend")],
        )


def test_gamespec_strips_blank_acceptance():
    spec = _valid_spec(acceptance=["  boots  ", "", "  ", "score"])
    assert spec.acceptance == ["boots", "score"]


def test_gamespec_empty_entities_allowed():
    """Empty list is ok before designer fills entities; player check only if non-empty."""
    spec = _valid_spec(entities=[])
    assert spec.entities == []


def test_pipeline_state_append_trace():
    state = PipelineState(run_id="run-1", prompt="space shooter")
    assert state.status == PipelineStatus.CREATED
    state.append_trace(TraceKind.THOUGHT, "clarify", "Need uniqueness knobs")
    assert len(state.trace) == 1
    assert state.trace[0].kind == TraceKind.THOUGHT
    assert state.trace[0].node == "clarify"
