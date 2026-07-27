"""GameSpec and pipeline state — structured contracts (source of truth)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Genre(str, Enum):
    SHOOTER = "shooter"
    RUNNER = "runner"
    PUZZLE = "puzzle"


class PipelineStatus(str, Enum):
    CREATED = "created"
    CLARIFYING = "clarifying"
    SPEC_LOCKED = "spec_locked"
    DESIGNING = "designing"
    CODING = "coding"
    TESTING = "testing"
    REPAIRING = "repairing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"


class TraceKind(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"


class ControlScheme(BaseModel):
    """Keyboard / pointer mapping for the generated game."""

    move: str = Field(default="arrows", description="e.g. arrows, wasd")
    action: str = Field(default="space", description="primary action key")
    notes: str = ""


class EntitySpec(BaseModel):
    id: str
    role: str = Field(..., description="player | enemy | projectile | pickup | obstacle")
    behavior: str = ""
    count: int | None = None


class WinLoseSpec(BaseModel):
    win: str = Field(..., min_length=1)
    lose: str = Field(..., min_length=1)


class ScoringSpec(BaseModel):
    events: list[str] = Field(default_factory=list)
    win_score: int | None = None


class VisualSpec(BaseModel):
    palette: list[str] = Field(default_factory=lambda: ["#07141a", "#f0a202", "#3ecf8e"])
    art_vibe: str = "minimal geometric"
    notes: str = ""


class GameSpec(BaseModel):
    """Locked design contract — drives design, code, and acceptance tests."""

    genre: Genre
    title: str = Field(..., min_length=1, max_length=80)
    twist: str = Field(..., min_length=1, description="Uniqueness from clarifying answers")
    prompt: str = Field(..., min_length=1)
    controls: ControlScheme = Field(default_factory=ControlScheme)
    entities: list[EntitySpec] = Field(default_factory=list)
    win_lose: WinLoseSpec
    scoring: ScoringSpec = Field(default_factory=ScoringSpec)
    visual: VisualSpec = Field(default_factory=VisualSpec)
    acceptance: list[str] = Field(
        default_factory=list,
        description="Seed checklist items (boots, move, score, …)",
    )

    @field_validator("entities")
    @classmethod
    def _require_player(cls, value: list[EntitySpec]) -> list[EntitySpec]:
        if value and not any(e.role == "player" for e in value):
            raise ValueError("entities must include at least one with role=player")
        return value

    @field_validator("acceptance")
    @classmethod
    def _nonempty_acceptance_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned


class ClarifyQuestion(BaseModel):
    id: str
    text: str
    options: list[str] = Field(default_factory=list)


class TraceEvent(BaseModel):
    kind: TraceKind
    node: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class AcceptanceItem(BaseModel):
    id: str
    description: str
    passed: bool | None = None
    detail: str | None = None


class TestReport(BaseModel):
    passed: bool
    items: list[AcceptanceItem] = Field(default_factory=list)
    summary: str = ""


class DesignPlan(BaseModel):
    mechanics: str = ""
    asset_plan: str = ""
    acceptance_tests: list[AcceptanceItem] = Field(default_factory=list)


class PipelineState(BaseModel):
    """Mutable run state carried through the LangGraph pipeline."""

    run_id: str
    prompt: str
    status: PipelineStatus = PipelineStatus.CREATED
    clarify_round: int = 0
    questions: list[ClarifyQuestion] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    gamespec: GameSpec | None = None
    spec_locked: bool = False
    design: DesignPlan | None = None
    acceptance_tests: list[AcceptanceItem] = Field(default_factory=list)
    artifact_dir: str | None = None
    test_report: TestReport | None = None
    repair_count: int = 0
    repair_budget: int = 3
    play_url: str | None = None
    error: str | None = None
    summary: str | None = None
    trace: list[TraceEvent] = Field(default_factory=list)

    def append_trace(
        self,
        kind: TraceKind,
        node: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.trace.append(
            TraceEvent(kind=kind, node=node, message=message, data=data or {})
        )
