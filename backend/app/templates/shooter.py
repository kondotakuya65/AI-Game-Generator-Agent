"""Space-shooter Canvas template (filled by coder with GameSpec knobs)."""

from __future__ import annotations

from app.templates.base import TemplateContext, base_css, html_shell


def render(ctx: TemplateContext) -> dict[str, str]:
    return {
        "index.html": html_shell(ctx),
        "style.css": base_css(ctx),
        "game.js": _js(ctx),
    }


def _js(ctx: TemplateContext) -> str:
    return f"""/* Genre: shooter | twist: {ctx.twist} */
(function () {{
  const canvas = document.getElementById("game");
  const ctx2d = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const statusEl = document.getElementById("status");

  const ACCENT = "{ctx.accent}";
  const OK = "{ctx.ok}";
  const WIN = {ctx.win!r};
  const LOSE = {ctx.lose!r};

  let score = 0;
  let alive = true;
  let won = false;
  const keys = {{}};

  const player = {{ x: canvas.width / 2, y: canvas.height - 40, w: 28, h: 18, cool: 0 }};
  const bullets = [];
  const enemies = [];
  let spawnTimer = 0;
  let wave = 1;

  function spawnEnemy() {{
    enemies.push({{
      x: 40 + Math.random() * (canvas.width - 80),
      y: -20,
      w: 24,
      h: 18,
      vy: 1.2 + wave * 0.15,
    }});
  }}

  function setStatus(text) {{
    statusEl.textContent = text;
  }}

  function bumpScore(n) {{
    score += n;
    scoreEl.textContent = String(score);
  }}

  window.addEventListener("keydown", (e) => {{ keys[e.key] = true; }});
  window.addEventListener("keyup", (e) => {{ keys[e.key] = false; }});

  function update() {{
    if (!alive || won) return;

    const left = keys["ArrowLeft"] || keys["a"] || keys["A"];
    const right = keys["ArrowRight"] || keys["d"] || keys["D"];
    if (left) player.x -= 5;
    if (right) player.x += 5;
    player.x = Math.max(0, Math.min(canvas.width - player.w, player.x));

    if ((keys[" "] || keys["Spacebar"]) && player.cool <= 0) {{
      bullets.push({{ x: player.x + player.w / 2 - 2, y: player.y, w: 4, h: 10, vy: -8 }});
      player.cool = 12;
    }}
    if (player.cool > 0) player.cool -= 1;

    for (const b of bullets) b.y += b.vy;
    for (let i = bullets.length - 1; i >= 0; i--) {{
      if (bullets[i].y < -10) bullets.splice(i, 1);
    }}

    spawnTimer -= 1;
    if (spawnTimer <= 0) {{
      spawnEnemy();
      spawnTimer = Math.max(25, 70 - wave * 5);
    }}
    for (const e of enemies) e.y += e.vy;

    for (let i = enemies.length - 1; i >= 0; i--) {{
      const e = enemies[i];
      if (e.y > canvas.height + 20) {{
        enemies.splice(i, 1);
        continue;
      }}
      // near-miss shield recharge flavor: skim past enemy edge
      const near =
        Math.abs(e.x + e.w / 2 - (player.x + player.w / 2)) < 50 &&
        Math.abs(e.y - player.y) < 40;
      if (near) setStatus("near-miss charge");

      if (rectsOverlap(player, e)) {{
        alive = false;
        setStatus("lose — " + LOSE);
      }}
      for (let j = bullets.length - 1; j >= 0; j--) {{
        if (rectsOverlap(bullets[j], e)) {{
          bullets.splice(j, 1);
          enemies.splice(i, 1);
          bumpScore(100);
          if (score >= 500) {{
            won = true;
            setStatus("win — " + WIN);
          }} else if (score % 200 === 0) {{
            wave += 1;
          }}
          break;
        }}
      }}
    }}
  }}

  function rectsOverlap(a, b) {{
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }}

  function draw() {{
    ctx2d.clearRect(0, 0, canvas.width, canvas.height);
    ctx2d.fillStyle = ACCENT;
    ctx2d.fillRect(player.x, player.y, player.w, player.h);
    ctx2d.fillStyle = OK;
    for (const b of bullets) ctx2d.fillRect(b.x, b.y, b.w, b.h);
    ctx2d.fillStyle = "#e85d4c";
    for (const e of enemies) ctx2d.fillRect(e.x, e.y, e.w, e.h);
  }}

  function loop() {{
    update();
    draw();
    requestAnimationFrame(loop);
  }}

  setStatus("ready");
  loop();
}})();
"""
