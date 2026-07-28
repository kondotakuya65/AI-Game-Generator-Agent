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
    trace?: { kind?: string; node?: string; message?: string }[];
  };
};

export async function fetchHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`Health HTTP ${res.status}`);
  return res.json();
}

export async function createRun(prompt: string): Promise<RunSnapshot> {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Create run HTTP ${res.status}`);
  }
  return res.json();
}

export async function confirmRun(
  runId: string,
  answers: Record<string, string>,
): Promise<RunSnapshot> {
  const res = await fetch(`/api/runs/${runId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Confirm run HTTP ${res.status}`);
  }
  return res.json();
}

export const DEMO_PROMPT = "Make a new game like a space shooter.";
