# AI-Game-Generator-Agent

Portfolio sample: a **LangGraph game builder** that turns a natural-language prompt into a **playable HTML/Canvas/JS game**.

| Layer | Role |
| --- | --- |
| **Frontend** | Next.js studio — prompt, clarifying Q&A, live Thought/Action/Observation, play embed |
| **Backend** | FastAPI — runs API, SSE traces, artifact serve (`/play/{id}`) |
| **Agent** | LangGraph pipeline: clarify → lock GameSpec → design → code → test ⇄ repair → deploy |
| **LLM** | Env switch: Ollama / OpenAI / Anthropic / mock |
| **Output** | Static Canvas game + acceptance report under `artifacts/` |

Contrasts with [AI-Procurement-Agent](https://github.com/kondotakuya65/AI-Procurement-Agent): procurement **pauses for HITL** before send; this agent **clarifies once**, then runs **unattended** after GameSpec lock.

**Docs:** [Scenario](docs/01-scenario.md) · [Architecture](docs/02-architecture.md) · [Implementation plan](docs/03-implementation-plan.md) · [Docs index](docs/README.md)

---

## Status

**Phase A1 — Scaffold** (this branch). Health API + studio shell. Pipeline nodes land in later PRs.

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8200
```

Health: http://localhost:8200/api/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Studio: http://localhost:3002

Copy [`.env.example`](.env.example) to `.env` (defaults use `LLM_PROVIDER=mock`).

## Ports

| Service | Port |
| --- | --- |
| Game API | 8200 |
| Game Studio | 3002 |

Chosen to sit beside FinOps (`8000`/`3000`) and Procurement (`8100`/`3001`).

## License

MIT
