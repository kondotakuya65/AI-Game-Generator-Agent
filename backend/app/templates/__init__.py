"""Genre templates for HTML5 Canvas games (shooter / runner / puzzle)."""

from __future__ import annotations

from typing import Callable

from app.models import GameSpec, Genre
from app.templates import puzzle, runner, shooter
from app.templates.base import TemplateContext, html_shell

RenderFn = Callable[[TemplateContext], dict[str, str]]

GENRE_RENDERERS: dict[Genre, RenderFn] = {
    Genre.SHOOTER: shooter.render,
    Genre.RUNNER: runner.render,
    Genre.PUZZLE: puzzle.render,
}

SUPPORTED_GENRES = tuple(g.value for g in Genre)


def context_from_gamespec(spec: GameSpec) -> TemplateContext:
    palette = list(spec.visual.palette or [])
    bg = palette[0] if len(palette) > 0 else "#07141a"
    accent = palette[1] if len(palette) > 1 else "#f0a202"
    ok = palette[2] if len(palette) > 2 else "#3ecf8e"
    return TemplateContext(
        title=spec.title,
        twist=spec.twist,
        win=spec.win_lose.win,
        lose=spec.win_lose.lose,
        art_vibe=spec.visual.art_vibe,
        bg=bg,
        accent=accent,
        ok=ok,
        move=spec.controls.move,
        action=spec.controls.action,
    )


def render_genre_template(
    spec: GameSpec,
    *,
    run_id: str | None = None,
) -> dict[str, str]:
    """Return mapping of filename → file contents for the genre template."""
    ctx = context_from_gamespec(spec)
    renderer = GENRE_RENDERERS.get(spec.genre, shooter.render)
    files = renderer(ctx)
    if run_id:
        # Absolute asset URLs so /play/{id} (no trailing slash) still loads CSS/JS.
        files["index.html"] = html_shell(ctx, asset_base=f"/play/{run_id}/")
    return files
