"""Designer: mechanics + asset plan from a locked GameSpec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.llm.provider import LLMClient, get_llm_client
from app.models import DesignPlan, GameSpec
from app.agent.acceptance import build_acceptance_checklist

DESIGN_SYSTEM = """You are a game designer for HTML5 Canvas games.
Given a locked GameSpec JSON, write a short design plan.
Return plain text with exactly these headings:
MECHANICS:
<2-6 sentences: controls, core loop, how the twist works, win/lose>
ASSETS:
<1-4 sentences: canvas shapes/colors only — no external image files>
Do not invent a different genre than the GameSpec.
"""


def _section(text: str, heading: str) -> str:
    pattern = rf"{heading}\s*:?\s*(.*?)(?=\n[A-Z][A-Z0-9 _-]+:|\Z)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def parse_design_response(raw: str) -> tuple[str, str]:
    mechanics = _section(raw, "MECHANICS")
    assets = _section(raw, "ASSETS")
    if not mechanics:
        # whole body as mechanics if headings missing
        mechanics = raw.strip()
    if not assets:
        assets = "Canvas primitives only (rects, circles, triangles)."
    return mechanics, assets


def fallback_design(spec: GameSpec) -> DesignPlan:
    controls = f"{spec.controls.move} to move; {spec.controls.action} for primary action"
    entities = ", ".join(f"{e.id}({e.role})" for e in spec.entities) or "player + threats"
    mechanics = (
        f"{spec.title} ({spec.genre.value}): {controls}. "
        f"Core twist: {spec.twist}. "
        f"Entities: {entities}. "
        f"Win when {spec.win_lose.win}; lose when {spec.win_lose.lose}. "
        f"Scoring: {', '.join(spec.scoring.events) or 'progress events'}."
    )
    palette = ", ".join(spec.visual.palette) if spec.visual.palette else "dark + accent"
    assets = (
        f"Art vibe: {spec.visual.art_vibe}. Palette: {palette}. "
        "Draw with canvas shapes only — no image assets."
    )
    return DesignPlan(
        mechanics=mechanics,
        asset_plan=assets,
        acceptance_tests=build_acceptance_checklist(spec),
    )


def build_design_plan(
    spec: GameSpec,
    *,
    client: LLMClient | None = None,
) -> tuple[DesignPlan, str]:
    llm = client or get_llm_client()
    checklist = build_acceptance_checklist(spec)
    user = (
        "Locked GameSpec:\n"
        f"{spec.model_dump_json(indent=2)}\n\n"
        "Write the MECHANICS and ASSETS plan now."
    )
    try:
        raw = llm.complete(DESIGN_SYSTEM, user)
        mechanics, assets = parse_design_response(raw)
        if len(mechanics) < 20:
            raise ValueError("mechanics too short")
        return (
            DesignPlan(
                mechanics=mechanics,
                asset_plan=assets,
                acceptance_tests=checklist,
            ),
            "llm",
        )
    except Exception:
        plan = fallback_design(spec)
        return plan, "fallback"


def design_dir(run_id: str, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return Path(settings.artifacts_dir) / run_id


def write_design_artifacts(
    run_id: str,
    plan: DesignPlan,
    settings: Settings | None = None,
) -> dict[str, str]:
    """Write design.md + design.json + acceptance.json; return path map."""
    root = design_dir(run_id, settings)
    root.mkdir(parents=True, exist_ok=True)
    acceptance_lines = "\n".join(
        f"- [{it.id}] {it.description}" for it in plan.acceptance_tests
    )
    md = (
        f"# Design — {run_id}\n\n"
        f"## Mechanics\n\n{plan.mechanics}\n\n"
        f"## Assets\n\n{plan.asset_plan}\n\n"
        f"## Acceptance\n\n{acceptance_lines or '_none_'}\n"
    )
    md_path = root / "design.md"
    json_path = root / "design.json"
    acceptance_path = root / "acceptance.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    acceptance_path.write_text(
        json.dumps(
            [it.model_dump(mode="json") for it in plan.acceptance_tests],
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "design_md": str(md_path),
        "design_json": str(json_path),
        "acceptance_json": str(acceptance_path),
    }


def design_from_gamespec(
    gamespec: dict[str, Any] | GameSpec,
    run_id: str,
    *,
    client: LLMClient | None = None,
    settings: Settings | None = None,
) -> tuple[DesignPlan, dict[str, str], str]:
    spec = gamespec if isinstance(gamespec, GameSpec) else GameSpec.model_validate(gamespec)
    plan, source = build_design_plan(spec, client=client)
    paths = write_design_artifacts(run_id, plan, settings=settings)
    return plan, paths, source
