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

export async function fetchHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`Health HTTP ${res.status}`);
  return res.json();
}

export const DEMO_PROMPT = "Make a new game like a space shooter.";
