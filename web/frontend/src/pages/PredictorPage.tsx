import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getFighters, predict, startSubscription, PaywallError, AuthError } from "../api";
import type { PredictResult } from "../api";
import { FighterSelect } from "../components/FighterSelect";
import { ResultCard } from "../components/ResultCard";
import { UpcomingPredictions } from "../components/UpcomingPredictions";
import { DreamFights } from "../components/DreamFights";

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

  // Section header, matching the landing page's idiom exactly. Deliberately not
  // the pixel display font — that face is reserved for page titles and card
  // internals; using it here made every block shout at the same volume.
  const heading = (text: string) => (
    <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">{text}</h2>
  );

  return (
    <div className="mx-auto w-full max-w-6xl px-4 text-left">
      <section className="py-10 text-center">
        <h1>STEADYFIGHTS</h1>
        {justSubscribed && (
          <p className="subtitle" style={{ color: "#4ade80" }}>
            You're subscribed! You just mad weight.
          </p>
        )}
      </section>

      {/* One row, gap-6, no per-child margins — the whole layout's rhythm comes
          from the two gaps, the way the landing page does it. */}
      <section className="flex flex-col gap-6 pb-16 lg:flex-row">
        {/* Center — the predictor itself, then the upcoming slate */}
        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <div>
            {heading(paywalled ? "Bout Brain" : "Predict a fight")}
            {paywalled ? (
              <div className="rounded-lg border border-zinc-700 p-6 text-center">
                <h2>Out of free predictions</h2>
                <p className="subtitle">
                  You've used all 10 free predictions. Subscribe for $10/month to keep going.
                </p>
                <button className="predict-btn" onClick={handleSubscribe} disabled={subscribing}>
                  {subscribing ? "Redirecting…" : "Subscribe — $10/mo"}
                </button>
              </div>
            ) : (
              <div className="rounded-lg border border-zinc-700 p-4">
                <div className="pickers">
                  <FighterSelect label="Fighter A" value={fighterA} onChange={setFighterA} options={fighters} />
                  <span className="vs">vs</span>
                  <FighterSelect label="Fighter B" value={fighterB} onChange={setFighterB} options={fighters} />
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
          </div>

          {result && <ResultCard result={result} />}

          <div>
            {heading("Quick predict")}
            <UpcomingPredictions
              known={fighters}
              paywalled={paywalled}
              onFreeLeft={setFreeLeft}
              onPaywall={() => setPaywalled(true)}
            />
          </div>
        </div>

        {/* Right — cross-era matchups. Shares this page's freeLeft/paywalled
            state, so a booking here spends the same allowance. */}
        <aside className="lg:w-80 lg:shrink-0">
          {heading("Dream fights")}
          <DreamFights
            paywalled={paywalled}
            onFreeLeft={setFreeLeft}
            onPaywall={() => setPaywalled(true)}
          />
        </aside>
      </section>
    </div>
  );
}

// Pull a readable message out of an unknown caught error.
function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}
