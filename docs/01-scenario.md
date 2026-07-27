# 01 — Project scenario

## One-line pitch

A player gives one prompt — *“Make a new game like a space shooter”* — and a LangGraph agent **clarifies uniqueness**, locks a **GameSpec**, then **designs → implements → tests → deploys** a playable HTML/Canvas/JS game **without further human intervention**.

## Why an agent (not another “GPT write me a game” chat)

| Sibling pattern | Game Generator |
| --- | --- |
| Resume / Code RAG — one question → one answer | One prompt → **multi-stage pipeline** |
| Procurement — tools + **HITL before send** | Clarify once, then **autonomous** after GameSpec lock |
| FinOps — retrieve + compute | **Generate artifact** + **executable acceptance tests** |

## Demo story

1. Open the Game Studio UI.  
2. Enter: *“Make a new game like a space shooter.”*  
3. Agent asks 3–5 short questions (twist, difficulty, win condition, art vibe).  
4. User confirms → **GameSpec** locked to `artifacts/{run_id}/gamespec.json`.  
5. Watch Thought → Action → Observation: design → code → test → (repair) → deploy.  
6. Open `/play/{id}` — playable Canvas game, no more human steps.

## Success criteria

- Clone runs with **mock LLM** (no API keys required for CI).  
- Clarifying phase is the **only** required human pause.  
- After lock, pipeline is autonomous with a **repair budget** and a clear stop/report.  
- Visible reasoning log + playable artifact (not a black-box spinner).  
- Golden path: space-shooter prompt → locked spec → boots, moves, scores.

## Out of scope (MVP)

- Unity / WebGL / native engines  
- Multiplayer / accounts / payments  
- Asset generation via image models (procedural / CSS / canvas shapes only)  
- Unlimited repair loops (hard budget `N`)  
