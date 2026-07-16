import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getFighters, predict, startSubscription, PaywallError, AuthError } from "../api";
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
  const [subscribing, setSubscribing] = useState<boolean>(false); // subscribe redirect in flight
  const [justSubscribed, setJustSubscribed] = useState<boolean>(false); // returned from checkout
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // effect. run one time on mount
  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e: unknown) => setError(errorMessage(e)));
  }, []);

  
  useEffect(() => {
    if (searchParams.get("subscribed") === "1") {
      setPaywalled(false); //set paywall to flase, open the gate
      setJustSubscribed(true); //flag
      setSearchParams({}, { replace: true }); // clean the URL so a refresh doesn't re-trigger
    }
  }, [searchParams, setSearchParams]);

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

  // send the user to Stripe Checkout for the $10/mo subscription
  async function handleSubscribe() {
    setError("");
    setSubscribing(true);
    try {
      const url = await startSubscription();
      window.location.href = url; // full-page redirect to Stripe
    } catch (e: unknown) {
      if (e instanceof AuthError) navigate("/login");
      else setError(errorMessage(e));
      setSubscribing(false); // only reset on failure — success navigates away
    }
  }

  return (
    <div className="page">
      <h1>STEADYFIGHTS</h1>
      <p className="subtitle"></p>
      <div className="flex flex-col items-center min-h-screen">
          {justSubscribed && (
              <p className="subtitle mt-6" style={{ color: "#4ade80" }}>
                  You're subscribed! You just mad weight.
              </p>
          )}
          {paywalled ? (
              <div className="border border-zinc-700 rounded-lg p-6 w-full max-w-xl mt-10 text-center">
                  <h2>Out of free predictions</h2>
                  <p className="subtitle">
                      You've used all 10 free predictions. Subscribe for $10/month to keep going.
                  </p>
                  <button
                      className="predict-btn"
                      onClick={handleSubscribe}
                      disabled={subscribing}
                  >
                      {subscribing ? "Redirecting…" : "Subscribe — $10/mo"}
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
