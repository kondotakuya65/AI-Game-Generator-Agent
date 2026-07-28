"""Simple puzzle Canvas template (click / match tiles)."""

from __future__ import annotations

from app.templates.base import TemplateContext, base_css, html_shell


def render(ctx: TemplateContext) -> dict[str, str]:
    return {
        "index.html": html_shell(ctx),
        "style.css": base_css(ctx),
        "game.js": _js(ctx),
    }


def _js(ctx: TemplateContext) -> str:
    return f"""/* Genre: puzzle | twist: {ctx.twist} */
(function () {{
  const canvas = document.getElementById("game");
  const ctx2d = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const statusEl = document.getElementById("status");

  const ACCENT = "{ctx.accent}";
  const OK = "{ctx.ok}";
  const WIN = {ctx.win!r};
  const LOSE = {ctx.lose!r};

  const COLS = 4;
  const ROWS = 3;
  const SIZE = 80;
  const OX = 80;
  const OY = 60;
  let score = 0;
  let selected = null;
  let moves = 12;
  let won = false;
  let lost = false;

  const colors = [ACCENT, OK, "#6c9bd1", "#c084fc"];
  const tiles = [];
  for (let r = 0; r < ROWS; r++) {{
    for (let c = 0; c < COLS; c++) {{
      tiles.push({{
        c, r,
        x: OX + c * (SIZE + 12),
        y: OY + r * (SIZE + 12),
        color: colors[(r + c) % colors.length],
        cleared: false,
      }});
    }}
  }}

  function setStatus(t) {{ statusEl.textContent = t; }}
  function bump(n) {{ score += n; scoreEl.textContent = String(score); }}

  canvas.addEventListener("click", (ev) => {{
    if (won || lost) return;
    const rect = canvas.getBoundingClientRect();
    const x = ((ev.clientX - rect.left) / rect.width) * canvas.width;
    const y = ((ev.clientY - rect.top) / rect.height) * canvas.height;
    const hit = tiles.find(
      (t) =>
        !t.cleared &&
        x >= t.x && x <= t.x + SIZE &&
        y >= t.y && y <= t.y + SIZE
    );
    if (!hit) return;
    if (!selected) {{
      selected = hit;
      setStatus("pick a match");
      return;
    }}
    moves -= 1;
    if (selected !== hit && selected.color === hit.color) {{
      selected.cleared = true;
      hit.cleared = true;
      selected = null;
      bump(50);
      setStatus("matched");
      if (tiles.every((t) => t.cleared)) {{
        won = true;
        setStatus("win — " + WIN);
      }}
    }} else {{
      selected = null;
      setStatus("no match · moves " + moves);
    }}
    if (!won && moves <= 0) {{
      lost = true;
      setStatus("lose — " + LOSE);
    }}
    draw();
  }});

  function draw() {{
    ctx2d.clearRect(0, 0, canvas.width, canvas.height);
    for (const t of tiles) {{
      if (t.cleared) continue;
      ctx2d.fillStyle = t === selected ? "#fff" : t.color;
      ctx2d.fillRect(t.x, t.y, SIZE, SIZE);
    }}
  }}

  setStatus("ready · moves " + moves);
  draw();
}})();
"""
