/** API helpers for the game studio UI. */

export type Health = {
  status: string;
  service: string;
  environment: string;
  llm_provider: string;
  llm_model: string;
  repair_budget: number;
  pipeline: string[];
};

export type ClarifyQuestion = {
  id: string;
  text: string;
  options?: string[];
};

export type RunInterrupt = {
  type?: string;
  prompt?: string;
  actions?: string[];
  questions?: ClarifyQuestion[];
  game_prompt?: string;
};

export type GameSpec = {
  genre?: string;
  title?: string;
  twist?: string;
  prompt?: string;
  acceptance?: string[];
  visual?: { art_vibe?: string };
  win_lose?: { win?: string; lose?: string };
};

export type TraceEvent = {
  kind?: string;
  node?: string;
  message?: string;
  data?: Record<string, unknown>;
};

export type RunSnapshot = {
  run_id: string;
  prompt: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  error?: string | null;
  summary?: string | null;
  interrupt?: RunInterrupt | null;
  state?: {
    questions?: ClarifyQuestion[];
    answers?: Record<string, string>;
    gamespec?: GameSpec | null;
    spec_locked?: boolean;
    play_url?: string | null;
    trace?: TraceEvent[];
  };
};

export type StreamEvent =
  | { type: "status"; run_id?: string; status?: string; prompt?: string; replay?: boolean }
  | { type: "node"; run_id?: string; node?: string }
  | {
      type: "progress";
      run_id?: string;
      message?: string;
      node?: string;
      phase?: string;
      data?: Record<string, unknown>;
    }
  | {
      type: "trace";
      run_id?: string;
      kind?: string;
      node?: string;
      message?: string;
      data?: Record<string, unknown>;
      replay?: boolean;
    }
  | { type: "interrupt"; run_id?: string; interrupt?: RunInterrupt; replay?: boolean }
  | ({ type: "done" } & Partial<RunSnapshot> & { replay?: boolean })
  | { type: "error"; run_id?: string; error?: string };

/**
 * SSE must hit FastAPI directly. Next.js rewrites can buffer proxied streams.
 */
function streamBaseUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8200";
  return raw.replace(/\/$/, "");
}

function streamUrl(path: string): string {
  return `${streamBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

export function playSrc(playUrl?: string | null): string | null {
  if (!playUrl) return null;
  const path = playUrl.startsWith("/") ? playUrl : `/${playUrl}`;
  const withSlash = path.endsWith("/") ? path : `${path}/`;
  // Hit FastAPI directly — avoids Next.js trailing-slash redirects breaking assets.
  return `${streamBaseUrl()}${withSlash}`;
}

export async function fetchHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`Health HTTP ${res.status}`);
  return res.json();
}

async function* readSse(res: Response): AsyncGenerator<StreamEvent> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (!res.body) throw new Error("No response body for SSE");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const lines = part.split("\n").map((l) => l.trim());
      const line = lines.find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice("data:".length).trim();
      if (!payload) continue;
      yield JSON.parse(payload) as StreamEvent;
    }
  }
}

export async function* streamCreateRun(prompt: string): AsyncGenerator<StreamEvent> {
  const res = await fetch(streamUrl("/api/runs/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ prompt }),
  });
  yield* readSse(res);
}

export async function* streamConfirmRun(
  runId: string,
  answers: Record<string, string>,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(streamUrl(`/api/runs/${runId}/confirm/stream`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ answers }),
  });
  yield* readSse(res);
}

export const DEMO_PROMPT = "Make a new game like a space shooter.";
