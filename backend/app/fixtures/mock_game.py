"""Deterministic offline GameSpec used by CODE_MODE=mock."""

from __future__ import annotations

from app.models import (
    ControlScheme,
    EntitySpec,
    GameSpec,
    Genre,
    ScoringSpec,
    VisualSpec,
    WinLoseSpec,
)


def mock_orbit_run_spec(prompt: str | None = None) -> GameSpec:
    """Fixed space-shooter spec — same bytes every offline demo."""
    return GameSpec(
        genre=Genre.SHOOTER,
        title="Orbit Run",
        twist="near-miss recharges shields",
        prompt=prompt or "Make a new game like a space shooter.",
        controls=ControlScheme(move="arrows", action="space", notes="difficulty=standard"),
        entities=[
            EntitySpec(id="player", role="player", behavior="ship", count=1),
            EntitySpec(id="drone", role="enemy", behavior="descend", count=8),
            EntitySpec(id="bolt", role="projectile", behavior="up", count=None),
        ],
        win_lose=WinLoseSpec(win="clear 5 waves / reach 500 score", lose="hull reaches 0"),
        scoring=ScoringSpec(events=["enemy destroyed +100"], win_score=500),
        visual=VisualSpec(
            palette=["#07141a", "#f0a202", "#3ecf8e"],
            art_vibe="minimal geometric",
        ),
        acceptance=[
            "game boots",
            "player can move",
            "player can shoot",
            "enemy exists",
            "score updates",
            "win or lose reachable",
        ],
    )
