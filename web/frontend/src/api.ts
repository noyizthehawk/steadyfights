// All communication with the Python backend lives here, so components don't
// have to know about URLs. If you deploy later, you only change this one line.
const BASE_URL = "http://localhost:8000";

// The exact shape of what /api/predict returns. This is the TypeScript payoff:
// every component that uses a prediction now KNOWS these fields (autocomplete +
// compile-time errors), instead of guessing at runtime.
export type PredictResult = {
  fighter_a: string;
  fighter_b: string;
  style_a: string;
  style_b: string;
  prob_a: number;
  prob_b: number;
  pick: string;
  confidence: number;
};

// Fetch the list of fighter names for the dropdowns.
export async function getFighters(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/api/fighters`);
  if (!res.ok) throw new Error("Could not load fighters");
  const data: { fighters: string[] } = await res.json();
  return data.fighters;
}

// Ask the model to predict a matchup. The return type tells callers exactly
// what they get back.
export async function predict(
  fighterA: string,
  fighterB: string,
): Promise<PredictResult> {
  const res = await fetch(`${BASE_URL}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fighter_a: fighterA, fighter_b: fighterB }),
  });
  if (!res.ok) {
    // FastAPI puts error text in `detail`.
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Prediction failed");
  }
  return res.json() as Promise<PredictResult>;
}
