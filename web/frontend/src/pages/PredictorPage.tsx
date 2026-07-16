import { useEffect, useState } from "react";
import { getFighters, predict, PaywallError } from "../api";
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
  const [paywalled, setPaywalled] = useState<boolean>(false); // out of free predictions?
  const [freeLeft, setFreeLeft] = useState<number | null>(null); // free predictions remaining

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
      setFreeLeft(data.free_remaining); // count winds down (null = unlimited)
    } catch (e: unknown) {
      if (e instanceof PaywallError) setPaywalled(true);
      else setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
    setFighterA("");
    setFighterB("");
  }

  return (
    <div className="page">
      <h1>STEADYFIGHTS</h1>
      <p className="subtitle"></p>
      <div className="flex flex-col items-center min-h-screen">
          {paywalled ? (
              <div className="border border-zinc-700 rounded-lg p-6 w-full max-w-xl mt-10 text-center">
                  <h2>Out of free predictions</h2>
                  <p className="subtitle">
                      You've used all 10 free predictions. Subscribe for $10/month to keep going.
                  </p>
                  {/* inert for now — stage 2 points this at Stripe checkout */}
                  <button
                      className="predict-btn"
                      onClick={() => setError("Subscriptions are coming soon.")}
                  >
                      Subscribe — $10/mo
                  </button>
              </div>
          ) : (
              <div className="border border-zinc-700 rounded-lg p-4 w-full max-w-xl mt-10 h-fit">
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
                  {freeLeft !== null && (
                      <p className="subtitle">
                          {freeLeft} free prediction{freeLeft === 1 ? "" : "s"} left
                      </p>
                  )}
              </div>
          )}

          {error && <p className="error">{error}</p>}
          {result && <ResultCard result={result} />}
      </div>
    </div>
  );
}

// Pull a readable message out of an unknown caught error.
function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}
