# 02 — Architecture

## High-level

```text
Next.js Studio  --SSE-->  FastAPI runs API  -->  LangGraph
                                                  |
                    +-----------------------------+----------------------+
                    |              |              |                      |
               Clarifier      Designer         Coder              Tester/Repair
               (Q&A→lock)   (plan+tests)   (HTML/Canvas/JS)      (accept→patch)
                                                                              |
                                                                         Deployer
                                                                      (/play/{id})
```

## Human vs autonomous boundary

```text
User prompt
  → Clarifier (human answers 3–5 questions)
  → Lock GameSpec          ← last required human step
  → Designer → Coder → Tester ⇄ Repair → Deployer
```

## LangGraph state (sketch)

```json
{
  "prompt": "Make a new game like a space shooter",
  "clarify_round": 0,
  "questions": [],
  "answers": {},
  "gamespec": null,
  "spec_locked": false,
  "design": null,
  "acceptance_tests": [],
  "artifact_dir": null,
  "test_report": null,
  "repair_count": 0,
  "repair_budget": 3,
  "play_url": null,
  "status": "clarifying",
  "trace": []
}
```

## GameSpec (source of truth)

Locked JSON drives design, code, and tests — not freeform chat memory.

| Field | Role |
| --- | --- |
| `genre` | shooter \| runner \| puzzle (template family) |
| `title` | display name |
| `twist` | uniqueness from clarifying answers |
| `controls` | keyboard / pointer mapping |
| `entities` | player, enemies, pickups, … |
| `win_lose` | win / lose conditions |
| `scoring` | how score updates |
| `visual` | palette / art vibe knobs |
| `acceptance` | machine-checkable checklist seeds |

## Pipeline nodes

| Node | Input | Output |
| --- | --- | --- |
| `clarify_ask` | prompt | uniqueness questions (checkpointed) |
| `clarify_gate` | questions | human answers via interrupt |
| `lock_spec` | answers + prompt | `gamespec.json` |
| `design` | GameSpec | mechanics plan + acceptance tests |
| `code` | GameSpec + design | `game/index.html`, `game.js`, … |
| `test` | acceptance + artifact | pass/fail report |
| `repair` | fail report + files | patched files (`repair_count++`) |
| `deploy` | artifact | `/play/{id}` + optional zip |

## Conditional edges

- `test` **pass** → `deploy`  
- `test` **fail** and `repair_count < budget` → `repair` → `test`  
- `test` **fail** and budget exhausted → end with failure report (no silent “success”)

## LLM coupling

- `LLM_PROVIDER=ollama|openai|anthropic|mock` — same env pattern as sibling repos.  
- Mock path returns fixture clarifier / designer / coder outputs so clone-and-run works offline.

## Ports

| Service | Port |
| --- | --- |
| Game API | **8200** |
| Game Studio UI | **3002** |
| Procurement (sibling) | 8100 / 3001 |
| FinOps (sibling) | 8000 / 3000 |

Avoids collisions when multiple portfolio apps run locally.
