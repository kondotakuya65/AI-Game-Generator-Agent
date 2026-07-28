# 03 — Implementation plan

Fine-grained checklist (one or few commits each). Merge feature PRs into `dev`; promote `dev` → `main` at demo checkpoints.

## Phase A — Foundation

### A1 — Scaffold ✅ (this PR)
- [x] README, license, `.gitignore`, `.env.example`  
- [x] Docs (scenario, architecture, plan)  
- [x] FastAPI health skeleton + smoke test  
- [x] Next.js studio shell (port 3002)  

**Accept:** `GET /api/health` OK; UI loads and shows health.

### A2 — Contracts + LLM adapter
- [x] GameSpec + pipeline state Pydantic models *(commit 1)*  
- [x] `ollama` / `openai` / `anthropic` / `mock` via `app.llm.provider` *(commit 2)*  
- [x] Unit tests (validation + mock LLM) *(commit 3)*  

**Accept:** invalid spec rejected; mock returns fixture text.

### A3 — LangGraph skeleton
- [x] `GameBuilderState`, node stubs, compile *(state + NODE_ORDER — commit 1)*  
- [x] Stub happy path emits thought / action / observation *(commit 2)*  
- [x] Conditional edge placeholder: test fail → repair *(commit 2)*  

**Accept:** `invoke` walks stub nodes offline; trace length matches node order.

## Phase B — Clarify → lock

### B1 — Clarifier
- [x] 3–5 uniqueness questions from prompt *(commit 1)*  
- [x] Lock `artifacts/{run_id}/gamespec.json` *(commit 2)*  
- [x] API + UI turn for answers / confirm *(commit 3)*  
- [x] Golden space-shooter lock test *(commit 4)*  

**Accept:** golden “space shooter” + fixture answers → valid locked GameSpec.

## Phase C — Design → code

### C1 — Designer
- [x] Mechanics + asset plan from GameSpec *(commit 1)*  
- [x] Executable acceptance checklist *(commit 2)*  

**Accept:** locked shooter → ≥5 acceptance items covering boots / move / score / win-lose.

### C2 — Coder
- [ ] Genre templates (shooter / runner / puzzle)  
- [ ] Write `index.html` + `game.js` (+ css)  
- [ ] Mock coder path for deterministic offline game  

**Accept:** required files present; canvas shell boots (mock path).

## Phase D — Test → repair → deploy

### D1 — Tester + repair
- [ ] Run acceptance checks on artifact  
- [ ] Repair loop with budget `N` + stop report  

**Accept:** failing fixture → repair → pass **or** clear failure report.

### D2 — Deployer
- [ ] Serve `/play/{id}` + zip download  

**Accept:** locked run → playable URL without further human input.

## Phase E — Studio + quality

### E1 — SSE + studio UI
- [ ] Stream thought / action / observation  
- [ ] Prompt, clarify panel, live trace, play embed  

**Accept:** mock end-to-end demo visible in UI.

### E2 — CI + docs
- [ ] GitHub Actions (backend pytest + frontend build)  
- [ ] Design decisions + README demo walkthrough  

**Accept:** CI green on PR; docs match shipped behavior.

## Stretch (optional)

- [ ] Playwright canvas interaction smokes  
- [ ] Gallery of past runs / regenerate from GameSpec  
- [ ] Reflection pass scores clarity before deploy  

## MVP ship line

**Through D2** = autonomous playable demo. **E1–E2** = portfolio-ready GitHub story. Stretch optional.

## Demo checkpoints (`dev` → `main`)

| After | Checkpoint |
| --- | --- |
| A1 | Scaffold runnable |
| B1 | Clarify + GameSpec demo |
| D2 | End-to-end game build |
| E2 | Portfolio ship |
