"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DEMO_PROMPT,
  confirmRun,
  createRun,
  fetchHealth,
  type ClarifyQuestion,
  type Health,
  type RunSnapshot,
} from "@/lib/api";

export function StudioShell() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState(DEMO_PROMPT);
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
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
    try {
      const snap = await createRun(prompt.trim());
      setRun(snap);
      const qs = snap.interrupt?.questions || [];
      const defaults: Record<string, string> = {};
      for (const q of qs) {
        if (q.options?.[0]) defaults[q.id] = q.options[0];
      }
      setAnswers(defaults);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start run");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!run) return;
    setBusy(true);
    setError(null);
    try {
      const snap = await confirmRun(run.run_id, answers);
      setRun(snap);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to confirm");
    } finally {
      setBusy(false);
    }
  }

  const gamespec = run?.state?.gamespec;
  const awaiting = run?.status === "awaiting_clarify";
  const completed = run?.status === "completed";

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-10 px-6 py-12">
      <header className="space-y-3">
        <p
          className="font-[family-name:var(--font-ibm)] text-xs tracking-[0.2em] uppercase"
          style={{ color: "var(--muted)" }}
        >
          Portfolio · Clarify → lock GameSpec
        </p>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Game Generator
        </h1>
        <p className="max-w-xl text-base leading-relaxed" style={{ color: "var(--muted)" }}>
          Prompt → clarify uniqueness → lock GameSpec. After confirm, the stub
          pipeline finishes autonomously (design → deploy stubs).
        </p>
      </header>

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
          {questions.map((q) => (
            <div key={q.id} className="space-y-2">
              <p className="text-sm font-semibold">{q.text}</p>
              {q.options && q.options.length > 0 ? (
                <select
                  value={answers[q.id] || ""}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  className="w-full rounded-md border bg-transparent px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)" }}
                >
                  {q.options.map((opt) => (
                    <option key={opt} value={opt} style={{ color: "#111" }}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  value={answers[q.id] || ""}
                  onChange={(e) =>
                    setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))
                  }
                  className="w-full rounded-md border bg-transparent px-3 py-2 text-sm"
                  style={{ borderColor: "var(--border)" }}
                />
              )}
            </div>
          ))}
          <button
            type="button"
            disabled={busy || Object.keys(answers).length === 0}
            onClick={onConfirm}
            className="rounded-md px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
            style={{ background: "var(--ok)", color: "#07141a" }}
          >
            {busy ? "Locking…" : "Confirm & lock GameSpec"}
          </button>
        </section>
      )}

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
            <div className="sm:col-span-2">
              <dt style={{ color: "var(--muted)" }}>win / lose</dt>
              <dd>
                {gamespec.win_lose?.win} / {gamespec.win_lose?.lose}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt style={{ color: "var(--muted)" }}>play url</dt>
              <dd style={{ color: "var(--ok)" }}>{run?.state?.play_url}</dd>
            </div>
          </dl>
        </section>
      )}

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
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 font-[family-name:var(--font-ibm)] text-sm sm:grid-cols-3">
            <div>
              <dt style={{ color: "var(--muted)" }}>status</dt>
              <dd style={{ color: "var(--ok)" }}>{health.status}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>llm</dt>
              <dd>
                {health.llm_provider}/{health.llm_model}
              </dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>run</dt>
              <dd>{run?.status || "—"}</dd>
            </div>
          </dl>
        )}
      </section>
    </main>
  );
}
