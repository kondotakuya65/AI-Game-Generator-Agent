# 04 — Design decisions

## LangGraph for an interruptible pipeline
Clarify needs a **checkpointed human pause**; test→repair needs a **cycle**. LangGraph state + interrupts fit better than a single chat completion or a fire-and-forget crew.

## Clarify once, then autonomous
Unlike [AI-Procurement-Agent](https://github.com/kondotakuya65/AI-Procurement-Agent) (HITL before every send), this agent asks uniqueness questions **once**, locks **GameSpec**, then runs design → code → test ⇄ repair → deploy unattended. The product story is “prompt → playable artifact,” not endless co-editing.

## Split `clarify_ask` / `clarify_gate`
LangGraph restarts an interrupted node from the top. Asking the LLM and calling `interrupt()` in the **same** node re-called the model on every confirm. Ask is checkpointed first; the gate only waits for answers.

## GameSpec is the contract
Downstream nodes read locked JSON (`gamespec.json`), not chat memory. Templates, acceptance checks, and repair all hang off that schema (`genre` ∈ shooter|runner|puzzle).

## Mock LLM + `CODE_MODE` for clone-and-run
`LLM_PROVIDER=mock` returns fixture clarify / lock / design text. `CODE_MODE=auto` writes the deterministic Orbit Run Canvas game when the provider is mock so CI and demos work offline. Real providers can still use genre templates (`template`) or auto.

## Tolerate messy local models
Small Ollama models often emit almost-JSON or wrong `genre` strings. Clarify pads missing option lists; lock **normalizes** genre / entities / `win_lose` before Pydantic validation, and falls back with an explicit `fallback:<reason>` in the trace when salvage fails.

## Static acceptance, not browser automation (MVP)
Tester inspects generated files for boots / move / score / win-lose signals. Fast, deterministic, CI-friendly. Playwright canvas smokes stay in stretch.

## Repair budget, not infinite loops
`REPAIR_BUDGET` (default 3) caps patch attempts. Exhaustion ends with a clear failure report — no silent “success.”

## SSE for Thought / Action / Observation
Same portfolio pattern as Procurement: stream traces over SSE. Studio hits FastAPI directly (`NEXT_PUBLIC_API_BASE`) so proxies don’t buffer event streams.

## Play URL vs Next trailing slashes
Next.js stripping `/play/{id}/` broke relative `game.js` / `style.css`. Studio embeds **FastAPI** play URLs; generated HTML uses absolute asset paths under `/play/{run_id}/`.

## Ports
| Service | Port |
| --- | --- |
| Game API | **8200** |
| Game Studio | **3002** |
| Procurement (sibling) | 8100 / 3001 |
| FinOps (sibling) | 8000 / 3000 |

Same LLM env knobs as siblings: `LLM_PROVIDER=ollama|openai|anthropic|mock`.
