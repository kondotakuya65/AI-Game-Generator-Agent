"use client";

import { useEffect, useState } from "react";
import { DEMO_PROMPT, fetchHealth, type Health } from "@/lib/api";

export function StudioShell() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState(DEMO_PROMPT);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((h) => {
        if (!cancelled) setHealth(h);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message || "API unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-10 px-6 py-12">
      <header className="space-y-3">
        <p
          className="font-[family-name:var(--font-ibm)] text-xs tracking-[0.2em] uppercase"
          style={{ color: "var(--muted)" }}
        >
          Portfolio · Phase A1 scaffold
        </p>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Game Generator
        </h1>
        <p className="max-w-xl text-base leading-relaxed" style={{ color: "var(--muted)" }}>
          Prompt → clarify uniqueness → lock GameSpec → design → code → test →
          deploy. Human only in clarify; autonomous after lock.
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
          className="w-full resize-y rounded-md border bg-transparent px-4 py-3 text-base outline-none"
          style={{
            borderColor: "var(--border)",
            background: "var(--panel)",
          }}
        />
        <button
          type="button"
          disabled
          className="rounded-md px-5 py-2.5 text-sm font-semibold opacity-60"
          style={{ background: "var(--accent)", color: "#111" }}
          title="Wired in later PRs"
        >
          Start build (coming next)
        </button>
      </section>

      <section
        className="space-y-3 rounded-md border px-5 py-4"
        style={{ borderColor: "var(--border)", background: "var(--panel)" }}
      >
        <h2 className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
          style={{ color: "var(--muted)" }}>
          API health
        </h2>
        {error && (
          <p className="text-sm" style={{ color: "#f87171" }}>
            {error} — start backend on :8200
          </p>
        )}
        {!error && !health && (
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
              <dt style={{ color: "var(--muted)" }}>repair budget</dt>
              <dd>{health.repair_budget}</dd>
            </div>
            <div className="col-span-2 sm:col-span-3">
              <dt style={{ color: "var(--muted)" }}>pipeline</dt>
              <dd className="mt-1 flex flex-wrap gap-2">
                {health.pipeline.map((step) => (
                  <span
                    key={step}
                    className="rounded border px-2 py-0.5 text-xs"
                    style={{ borderColor: "var(--border)" }}
                  >
                    {step}
                  </span>
                ))}
              </dd>
            </div>
          </dl>
        )}
      </section>
    </main>
  );
}
