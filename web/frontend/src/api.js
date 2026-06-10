// All communication with the Python backend lives here, so components don't
// have to know about URLs. If you deploy later, you only change this one line.
const BASE_URL = "http://localhost:8000";

// Fetch the list of fighter names for the dropdowns.
export async function getFighters() {
  const res = await fetch(`${BASE_URL}/api/fighters`);
  if (!res.ok) throw new Error("Could not load fighters");
  const data = await res.json();
  return data.fighters; // an array of strings
}

// Ask the model to predict a matchup. Returns the result object the
// backend's predict_fight_api() builds.
export async function predict(fighterA, fighterB) {
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
  return res.json();
}
