"""Endless-runner Canvas template."""

from __future__ import annotations

from app.templates.base import TemplateContext, base_css, html_shell


def render(ctx: TemplateContext) -> dict[str, str]:
    return {
        "index.html": html_shell(ctx),
        "style.css": base_css(ctx),
        "game.js": _js(ctx),
    }


def _js(ctx: TemplateContext) -> str:
    return f"""/* Genre: runner | twist: {ctx.twist} */
(function () {{
  const canvas = document.getElementById("game");
  const ctx2d = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const statusEl = document.getElementById("status");

  const ACCENT = "{ctx.accent}";
  const WIN = {ctx.win!r};
  const LOSE = {ctx.lose!r};

  let score = 0;
  let alive = true;
  let won = false;
  const lanes = [160, 320, 480];
  let lane = 1;
  const player = {{ x: lanes[lane], y: canvas.height - 60, w: 26, h: 26 }};
  const hazards = [];
  let spawn = 0;
  let speed = 4;

  window.addEventListener("keydown", (e) => {{
    if (e.key === "ArrowLeft" || e.key === "a") lane = Math.max(0, lane - 1);
    if (e.key === "ArrowRight" || e.key === "d") lane = Math.min(2, lane + 1);
    player.x = lanes[lane] - player.w / 2;
  }});

  function setStatus(t) {{ statusEl.textContent = t; }}
  function bump(n) {{ score += n; scoreEl.textContent = String(score); }}

  function update() {{
    if (!alive || won) return;
    spawn -= 1;
    if (spawn <= 0) {{
      const L = Math.floor(Math.random() * 3);
      hazards.push({{ x: lanes[L] - 14, y: -30, w: 28, h: 28, vy: speed }});
      spawn = 40;
    }}
    for (let i = hazards.length - 1; i >= 0; i--) {{
      const h = hazards[i];
      h.y += h.vy;
      if (h.y > canvas.height) {{
        hazards.splice(i, 1);
        bump(10);
        if (score >= 400) {{ won = true; setStatus("win — " + WIN); }}
        continue;
      }}
      if (overlap(player, h)) {{
        alive = false;
        setStatus("lose — " + LOSE);
      }}
    }}
    if (score > 0 && score % 100 === 0) speed = 4 + score / 100;
  }}

  function overlap(a, b) {{
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }}

  function draw() {{
    ctx2d.clearRect(0, 0, canvas.width, canvas.height);
    ctx2d.strokeStyle = "#1e3a44";
    for (const x of lanes) {{
      ctx2d.beginPath();
      ctx2d.moveTo(x, 0);
      ctx2d.lineTo(x, canvas.height);
      ctx2d.stroke();
    }}
    ctx2d.fillStyle = ACCENT;
    ctx2d.fillRect(player.x, player.y, player.w, player.h);
    ctx2d.fillStyle = "#e85d4c";
    for (const h of hazards) ctx2d.fillRect(h.x, h.y, h.w, h.h);
  }}

  function loop() {{ update(); draw(); requestAnimationFrame(loop); }}
  setStatus("ready");
  player.x = lanes[lane] - player.w / 2;
  loop();
}})();
"""
