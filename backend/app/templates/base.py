"""Shared HTML/CSS shell for Canvas genre templates."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TemplateContext:
    title: str = "Untitled Game"
    twist: str = "a unique mechanic"
    win: str = "reach the objective"
    lose: str = "player is defeated"
    art_vibe: str = "minimal geometric"
    bg: str = "#07141a"
    accent: str = "#f0a202"
    ok: str = "#3ecf8e"
    move: str = "arrows"
    action: str = "space"
    extra: dict = field(default_factory=dict)


def html_shell(ctx: TemplateContext, script_name: str = "game.js") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(ctx.title)}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <main class="wrap">
    <header class="bar">
      <h1 id="title">{_escape(ctx.title)}</h1>
      <p id="hud">Score: <span id="score">0</span> · Status: <span id="status">ready</span></p>
    </header>
    <canvas id="game" width="640" height="480" aria-label="{_escape(ctx.title)} canvas"></canvas>
    <p class="hint" id="hint">Twist: {_escape(ctx.twist)}</p>
  </main>
  <script src="{script_name}"></script>
</body>
</html>
"""


def base_css(ctx: TemplateContext) -> str:
    return f"""* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  min-height: 100%;
  background: {ctx.bg};
  color: #e6f2ef;
  font-family: "Segoe UI", system-ui, sans-serif;
}}
.wrap {{
  max-width: 680px;
  margin: 0 auto;
  padding: 1rem;
}}
.bar {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 0.75rem;
}}
h1 {{
  margin: 0;
  font-size: 1.25rem;
  letter-spacing: 0.02em;
}}
#hud {{
  margin: 0;
  font-size: 0.85rem;
  color: #8aa4a0;
}}
#game {{
  display: block;
  width: 100%;
  max-width: 640px;
  background: #0a1c24;
  border: 1px solid #1e3a44;
}}
.hint {{
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: #8aa4a0;
}}
"""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
