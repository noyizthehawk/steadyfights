import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getFighters, predict, startSubscription, PaywallError, AuthError } from "../api";
import type { PredictResult } from "../api";
import { FighterSelect } from "../components/FighterSelect";
import { ResultCard } from "../components/ResultCard";
import { UpcomingPredictions } from "../components/UpcomingPredictions";
import { DreamFights } from "../components/DreamFights";

// Ten dots instead of "2 free predictions left" — the count is glanceable and
// stops the line rewrapping as the number changes. The text still exists for
// screen readers, which can't read a row of divs.
function FreeDots({ left, total = 10 }: { left: number; total?: number }) {
  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-zinc-800 pt-3">
      <span className="text-[10px] uppercase tracking-widest text-zinc-500">Free predictions</span>
      <span
        className="flex items-center gap-1"
        role="img"
        aria-label={`${left} of ${total} free predictions remaining`}
      >
        {Array.from({ length: total }, (_, i) => (
          <span
            key={i}
            aria-hidden
            className={`h-1.5 w-1.5 rounded-full transition-colors ${
              i < left ? "bg-[#d33a2c]" : "bg-zinc-700"
            }`}
          />
        ))}
      </span>
    </div>
  );
}

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
      setPaywalled(false); //set paywall to false, open the gate
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
    <h2 className="mb-2.5 text-center text-[9px] font-medium uppercase tracking-[0.2em] text-zinc-500 sm:mb-3 sm:text-[10px]">{text}</h2>
  );

  return (
    <div className="mx-auto w-full max-w-6xl px-3 text-left sm:px-4">
      <section className="py-5 text-center sm:py-9">
        <h1>FIGHTS, FIGURED OUT.</h1>
        {justSubscribed && (
          <p className="subtitle" style={{ color: "#4ade80" }}>
            You're subscribed! You just made weight.
          </p>
        )}
      </section>

      {/* One row, gap-6, no per-child margins — the whole layout's rhythm comes
          from the two gaps, the way the landing page does it. */}
      <section className="flex flex-col gap-5 pb-12 sm:gap-6 sm:pb-16 lg:flex-row">
        {/* Center — the predictor itself, then the upcoming slate */}
        <div className="flex min-w-0 flex-1 flex-col gap-5 sm:gap-6">
          <div>
            {heading(paywalled ? "Bout Brain" : "Predict a fight")}
            {paywalled ? (
              <div className="rounded-xl border border-zinc-800 bg-black p-5 text-center sm:p-6">
                <h2>Out of free predictions</h2>
                <p className="subtitle">
                  You've used all 10 free predictions. Subscribe for $10/month to keep going.
                </p>
                <button className="predict-btn" onClick={handleSubscribe} disabled={subscribing}>
                  {subscribing ? "Redirecting…" : "Subscribe — $10/mo"}
                </button>
              </div>
            ) : (
              <div className="rounded-xl border border-zinc-800 bg-black p-3.5 sm:p-4">
                <div className="pickers">
                  <FighterSelect label="Fighter A" value={fighterA} onChange={setFighterA} options={fighters} />
                  <span className="vs">vs</span>
                  <FighterSelect label="Fighter B" value={fighterB} onChange={setFighterB} options={fighters} />
                </div>
                <button className="predict-btn" onClick={handlePredict} disabled={loading}>
                  {loading ? "Predicting…" : "Predict"}
                </button>
                {freeLeft !== null && <FreeDots left={freeLeft} />}
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
