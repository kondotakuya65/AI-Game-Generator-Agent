"use client";

import type { TraceEvent } from "@/lib/api";

type TraceLogProps = {
  events: TraceEvent[];
  busy: boolean;
  liveActivity?: string | null;
};

function kindColor(kind?: string) {
  switch (kind) {
    case "thought":
      return "#7dd3fc";
    case "action":
      return "var(--accent)";
    case "observation":
      return "var(--ok)";
    default:
      return "var(--muted)";
  }
}

export function TraceLog({ events, busy, liveActivity }: TraceLogProps) {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2
          className="font-[family-name:var(--font-ibm)] text-xs tracking-wider uppercase"
          style={{ color: "var(--muted)" }}
        >
          Thought / Action / Observation
        </h2>
        <span
          className="font-[family-name:var(--font-ibm)] text-xs"
          style={{ color: "var(--muted)" }}
        >
          {events.length} step{events.length === 1 ? "" : "s"}
          {busy ? " · live" : ""}
        </span>
      </div>
      {busy && liveActivity ? (
        <p
          className="animate-pulse rounded-md border px-3 py-2 font-[family-name:var(--font-ibm)] text-xs"
          style={{ borderColor: "var(--border)", color: "#7dd3fc" }}
        >
          {liveActivity}
        </p>
      ) : null}
      <div
        className="max-h-80 space-y-2 overflow-y-auto rounded-md border px-4 py-3"
        style={{ borderColor: "var(--border)", background: "var(--panel)" }}
      >
        {events.length === 0 && !liveActivity ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Start a build to stream agent steps here.
          </p>
        ) : (
          events.map((ev, idx) => (
            <article
              key={`${ev.node}-${idx}-${ev.message?.slice(0, 24)}`}
              className="border-b pb-2 last:border-0"
              style={{ borderColor: "var(--border)" }}
            >
              <div className="mb-1 flex flex-wrap items-center gap-2 font-[family-name:var(--font-ibm)] text-[11px]">
                <span style={{ color: kindColor(ev.kind) }}>{ev.kind || "event"}</span>
                <span style={{ color: "var(--muted)" }}>·</span>
                <span>{ev.node}</span>
              </div>
              <p className="text-sm leading-relaxed opacity-90">{ev.message}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
