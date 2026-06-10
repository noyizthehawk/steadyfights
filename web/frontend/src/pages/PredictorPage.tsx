import { useEffect, useState } from "react";
import { getFighters, predict } from "../api";
import type { PredictResult } from "../api";
import { FighterSelect } from "../components/FighterSelect";
import { ResultCard } from "../components/ResultCard";

export default function PredictorPage() {
  // state
  const [fighters, setFighters] = useState<string[]>([]); // names for the dropdowns
  const [fighterA, setFighterA] = useState<string>(""); // selected A
  const [fighterB, setFighterB] = useState<string>(""); // selected B
  const [result, setResult] = useState<PredictResult | null>(null); // prediction, or none yet
  const [loading, setLoading] = useState<boolean>(false); // request in flight?
  const [error, setError] = useState<string>(""); // error message to show

  // effect. run one time on mount
  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e: unknown) => setError(errorMessage(e)));
  }, []);

  // prediction handler
  async function handlePredict() {
    setError("");
    setResult(null);
    if (!fighterA || !fighterB) {
      setError("Pick both fighters.");
      return;
    }
    setLoading(true);
    try {
      const data = await predict(fighterA, fighterB);
      setResult(data);
    } catch (e: unknown) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>STEADYFIGHTS</h1>
      <p className="subtitle">Best Model on the market</p>

      <div className="pickers">
        <FighterSelect
          label="Fighter A"
          value={fighterA}
          onChange={setFighterA}
          options={fighters}
        />
        <span className="vs">vs</span>
        <FighterSelect
          label="Fighter B"
          value={fighterB}
          onChange={setFighterB}
          options={fighters}
        />
      </div>

      <button className="predict-btn" onClick={handlePredict} disabled={loading}>
        {loading ? "Predicting…" : "Predict"}
      </button>

      {/* Conditional rendering: only show these if they exist. */}
      {error && <p className="error">{error}</p>}
      {result && <ResultCard result={result} />}
    </div>
  );
}

// Pull a readable message out of an unknown caught error.
function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}
