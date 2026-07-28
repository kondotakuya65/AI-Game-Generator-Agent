"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DEMO_PROMPT,
  fetchHealth,
  playSrc,
  streamConfirmRun,
  streamCreateRun,
  type ClarifyQuestion,
  type Health,
  type RunSnapshot,
  type TraceEvent,
} from "@/lib/api";
import { TraceLog } from "@/components/TraceLog";

export function StudioShell() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState(DEMO_PROMPT);
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [liveActivity, setLiveActivity] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((h) => {
        if (!cancelled) setHealth(h);
      })
      .catch((e: Error) => {
        if (!cancelled) setHealthError(e.message || "API unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const questions: ClarifyQuestion[] = useMemo(() => {
    return run?.interrupt?.questions || run?.state?.questions || [];
  }, [run]);

  async function onStart() {
    setBusy(true);
    setError(null);
    setRun(null);
    setAnswers({});
    setTraces([]);
    setLiveActivity("Starting clarify…");
    try {
      let snap: RunSnapshot | null = null;
      for await (const ev of streamCreateRun(prompt.trim())) {
        if (ev.type === "status") {
          setLiveActivity(`Run ${ev.run_id?.slice(0, 8)}…`);
        } else if (ev.type === "node") {
          setLiveActivity(`Node: ${ev.node}`);
        } else if (ev.type === "progress") {
          setLiveActivity(ev.message || "Working…");
        } else if (ev.type === "trace") {
          setTraces((prev) => [
            ...prev,
            {
              kind: ev.kind,
              node: ev.node,
              message: ev.message,
              data: ev.data,
            },
          ]);
        } else if (ev.type === "interrupt") {
          snap = {
            run_id: ev.run_id || "",
            prompt: prompt.trim(),
            status: "awaiting_clarify",
            interrupt: ev.interrupt,
          };
          setRun(snap);
          const qs = ev.interrupt?.questions || [];
          const defaults: Record<string, string> = {};
          for (const q of qs) {
            if (q.options?.[0]) defaults[q.id] = q.options[0];
          }
          setAnswers(defaults);
          setLiveActivity("Awaiting uniqueness answers");
        } else if (ev.type === "done") {
          snap = {
            run_id: ev.run_id || snap?.run_id || "",
            prompt: ev.prompt || prompt.trim(),
            status: ev.status || "awaiting_clarify",
            summary: ev.summary,
            interrupt: ev.interrupt ?? snap?.interrupt,
            state: ev.state,
          };
          setRun(snap);
          if (ev.state?.trace?.length) {
            setTraces(ev.state.trace);
          }
        } else if (ev.type === "error") {
          throw new Error(ev.error || "Stream error");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start run");
    } finally {
      setBusy(false);
      setLiveActivity(null);
    }
  }

  async function onConfirm() {
    if (!run) return;
    setBusy(true);
    setError(null);
    setLiveActivity("Locking GameSpec…");
    try {
      for await (const ev of streamConfirmRun(run.run_id, answers)) {
        if (ev.type === "status") {
          setLiveActivity("Building autonomously…");
        } else if (ev.type === "node") {
          setLiveActivity(`Node: ${ev.node}`);
        } else if (ev.type === "progress") {
          setLiveActivity(ev.message || "Working…");
        } else if (ev.type === "trace") {
          setTraces((prev) => [
            ...prev,
            {
              kind: ev.kind,
              node: ev.node,
              message: ev.message,
              data: ev.data,
            },
          ]);
        } else if (ev.type === "done") {
          setRun({
            run_id: ev.run_id || run.run_id,
            prompt: ev.prompt || run.prompt,
            status: ev.status || "completed",
            summary: ev.summary,
            interrupt: null,
            state: ev.state,
          });
          if (ev.state?.trace?.length) {
            setTraces(ev.state.trace);
          }
        } else if (ev.type === "error") {
          throw new Error(ev.error || "Confirm stream error");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to confirm");
    } finally {
      setBusy(false);
      setLiveActivity(null);
    }
  }

  const gamespec = run?.state?.gamespec;
  const awaiting = run?.status === "awaiting_clarify";
  const completed = run?.status === "completed";
  const embed = playSrc(run?.state?.play_url);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-10 px-6 py-12">
      <header className="space-y-3">
        <p
          className="font-[family-name:var(--font-ibm)] text-xs tracking-[0.2em] uppercase"
          style={{ color: "var(--muted)" }}
        >
          Portfolio · Clarify → autonomous build
        </p>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Game Generator
        </h1>
        <p className="max-w-xl text-base leading-relaxed" style={{ color: "var(--muted)" }}>
          Prompt → uniqueness Q&A → lock GameSpec → design → code → test →
          deploy. Watch the live trace, then play in-studio.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-8">
          <section className="space-y-3">
            <label
              htmlFor="prompt"
              className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
              style={{ color: "var(--muted)" }}
            >
              Game prompt
            </label>
            <textarea
              id="prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={busy || awaiting}
              className="w-full resize-y rounded-md border bg-transparent px-4 py-3 text-base outline-none disabled:opacity-60"
              style={{
                borderColor: "var(--border)",
                background: "var(--panel)",
              }}
            />
            <button
              type="button"
              disabled={busy || prompt.trim().length < 3 || awaiting}
              onClick={onStart}
              className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
              style={{ background: "var(--accent)", color: "#111" }}
            >
              {busy && !awaiting ? "Starting…" : "Start clarify"}
            </button>
          </section>

          {error && (
            <p className="text-sm" style={{ color: "#f87171" }}>
              {error}
            </p>
          )}

          {awaiting && questions.length > 0 && (
            <section
              className="space-y-4 rounded-md border px-5 py-4"
              style={{ borderColor: "var(--border)", background: "var(--panel)" }}
            >
              <h2
                className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
                style={{ color: "var(--muted)" }}
              >
                Uniqueness questions
              </h2>
              {questions.map((q) => {
                const opts = q.options || [];
                const selected = answers[q.id] || "";
                const isPreset = opts.includes(selected);
                return (
                  <div key={q.id} className="space-y-2">
                    <p className="text-sm font-semibold">{q.text}</p>
                    {opts.length > 0 && (
                      <div
                        className="flex flex-col gap-2"
                        role="group"
                        aria-label={q.text}
                      >
                        {opts.map((opt) => {
                          const active = selected === opt;
                          return (
                            <button
                              key={opt}
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                setAnswers((prev) => ({ ...prev, [q.id]: opt }))
                              }
                              className="rounded-md border px-3 py-2 text-left text-sm transition-colors disabled:opacity-50"
                              style={{
                                borderColor: active
                                  ? "var(--accent)"
                                  : "var(--border)",
                                background: active
                                  ? "color-mix(in srgb, var(--accent) 22%, transparent)"
                                  : "transparent",
                                color: "var(--foreground)",
                              }}
                            >
                              {opt}
                            </button>
                          );
                        })}
                      </div>
                    )}
                    <label className="block space-y-1">
                      <span
                        className="font-[family-name:var(--font-ibm)] text-[11px] tracking-wider uppercase"
                        style={{ color: "var(--muted)" }}
                      >
                        {opts.length > 0 ? "Or write your own" : "Your answer"}
                      </span>
                      <input
                        value={isPreset ? "" : selected}
                        placeholder={
                          opts.length > 0
                            ? "Custom answer…"
                            : "Type an answer…"
                        }
                        onChange={(e) =>
                          setAnswers((prev) => ({
                            ...prev,
                            [q.id]: e.target.value,
                          }))
                        }
                        disabled={busy}
                        className="w-full rounded-md border bg-transparent px-3 py-2 text-sm outline-none disabled:opacity-50"
                        style={{ borderColor: "var(--border)" }}
                      />
                    </label>
                  </div>
                );
              })}
              <button
                type="button"
                disabled={
                  busy ||
                  questions.some((q) => !(answers[q.id] || "").trim())
                }
                onClick={onConfirm}
                className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
                style={{ background: "var(--ok)", color: "#07141a" }}
              >
                {busy ? "Building…" : "Confirm & lock GameSpec"}
              </button>
            </section>
          )}

          <TraceLog events={traces} busy={busy} liveActivity={liveActivity} />
        </div>

        <div className="space-y-8">
          {completed && gamespec && (
            <section
              className="space-y-3 rounded-md border px-5 py-4"
              style={{ borderColor: "var(--border)", background: "var(--panel)" }}
            >
              <h2
                className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
                style={{ color: "var(--muted)" }}
              >
                Locked GameSpec
              </h2>
              <dl className="grid gap-2 font-[family-name:var(--font-ibm)] text-sm sm:grid-cols-2">
                <div>
                  <dt style={{ color: "var(--muted)" }}>title</dt>
                  <dd>{gamespec.title}</dd>
                </div>
                <div>
                  <dt style={{ color: "var(--muted)" }}>genre</dt>
                  <dd>{gamespec.genre}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt style={{ color: "var(--muted)" }}>twist</dt>
                  <dd>{gamespec.twist}</dd>
                </div>
              </dl>
            </section>
          )}

          <section
            className="space-y-3 rounded-md border px-5 py-4"
            style={{ borderColor: "var(--border)", background: "var(--panel)" }}
          >
            <div className="flex items-baseline justify-between gap-3">
              <h2
                className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
                style={{ color: "var(--muted)" }}
              >
                Play
              </h2>
              {embed && (
                <a
                  href={embed}
                  target="_blank"
                  rel="noreferrer"
                  className="font-[family-name:var(--font-ibm)] text-xs"
                  style={{ color: "var(--ok)" }}
                >
                  open ↗
                </a>
              )}
            </div>
            {embed ? (
              <iframe
                title="Generated game"
                src={embed}
                className="h-[420px] w-full rounded-md border"
                style={{ borderColor: "var(--border)", background: "#000" }}
              />
            ) : (
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                After confirm, the playable Canvas game embeds here.
              </p>
            )}
            {completed && embed && (
              <p className="font-[family-name:var(--font-ibm)] text-xs" style={{ color: "var(--muted)" }}>
                <a href={embed} target="_blank" rel="noreferrer" style={{ color: "var(--ok)" }}>
                  {embed}
                </a>
                {" · "}
                <a
                  href={`/api/runs/${run!.run_id}/download`}
                  className="underline"
                  style={{ color: "var(--ok)" }}
                >
                  download zip
                </a>
              </p>
            )}
          </section>

          <section
            className="space-y-3 rounded-md border px-5 py-4"
            style={{ borderColor: "var(--border)", background: "var(--panel)" }}
          >
            <h2
              className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
              style={{ color: "var(--muted)" }}
            >
              API health
            </h2>
            {healthError && (
              <p className="text-sm" style={{ color: "#f87171" }}>
                {healthError} — start backend on :8200
              </p>
            )}
            {!healthError && !health && (
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Checking…
              </p>
            )}
            {health && (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 font-[family-name:var(--font-ibm)] text-sm">
                <div>
                  <dt style={{ color: "var(--muted)" }}>status</dt>
                  <dd style={{ color: "var(--ok)" }}>{health.status}</dd>
                </div>
                <div>
                  <dt style={{ color: "var(--muted)" }}>run</dt>
                  <dd>{run?.status || "—"}</dd>
                </div>
              </dl>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
