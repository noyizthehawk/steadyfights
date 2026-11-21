import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getFighters, me, predict, startSubscription, PaywallError, AuthError } from "../api";
import type { PredictResult } from "../api";
import { FighterSelect } from "../components/FighterSelect";
import { ResultCard } from "../components/ResultCard";
import { UpcomingPredictions } from "../components/UpcomingPredictions";
import { DreamFights } from "../components/DreamFights";
import { BoutBrainRecord } from "../components/BoutBrainRecord";

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

type SubState = "confirming" | "active" | "slow";

// Shown after returning from Stripe Checkout. Waits for the webhook before
// saying "unlocked", so it never promises access the backend hasn't granted.
function SubscribedPanel({ state, onClose }: { state: SubState; onClose: () => void }) {
  const done = state === "active";
  const accent = done ? "#34d399" : "#fbbf24";
  return (
    <div
      role="status"
      className="relative mx-auto mt-5 max-w-md rounded-xl border bg-black p-5 text-left sm:mt-6"
      style={{ borderColor: `${accent}4d` }}
    >
      {done && (
        <button
          onClick={onClose}
          aria-label="Dismiss"
          className="absolute right-3 top-3 p-1 text-zinc-500 transition-colors hover:text-white"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      )}
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden
          className={`block h-2 w-2 rounded-full ${done ? "" : "animate-pulse"}`}
          style={{ background: accent, boxShadow: `0 0 0 4px ${accent}22` }}
        />
        <span className="text-[11px] leading-none" style={{ fontFamily: "var(--font-display)", color: accent }}>
          {done ? "YOU MADE WEIGHT" : "WEIGHING IN"}
        </span>
      </div>
      <div
        className="mt-4 space-y-1.5 border-l-2 pl-3 text-sm italic text-zinc-300"
        style={{ fontFamily: "var(--font-rundown)", borderColor: accent }}
      >
        {state === "confirming" && <p>Payment received — unlocking Bout Brain…</p>}
        {state === "active" && (
          <>
            <p>Bout Brain is unlocked.</p>
            <p>Unlimited predictions, every card.</p>
            <p className="text-zinc-500">
              Manage your plan any time from{" "}
              <Link to="/account" className="underline decoration-zinc-600 underline-offset-4 hover:text-zinc-200">
                Account
              </Link>
              .
            </p>
          </>
        )}
        {state === "slow" && (
          <>
            <p>Payment received — it's taking longer than usual to unlock.</p>
            <p className="text-zinc-500">Refresh in a minute. You won't be charged twice.</p>
          </>
        )}
      </div>
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
  // returned from checkout: confirming (webhook not landed yet) → active, or slow if it never shows
  const [subState, setSubState] = useState<SubState | null>(null);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // effect. run one time on mount
  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e: unknown) => setError(errorMessage(e)));
  }, []);

  
  useEffect(() => {
    if (searchParams.get("subscribed") !== "1") return;
    setPaywalled(false); //set paywall to false, open the gate
    setSearchParams({}, { replace: true }); // clean the URL so a refresh doesn't re-trigger
    setSubState("confirming");
  }, [searchParams, setSearchParams]);

  // Stripe redirects here before its webhook reaches us, so poll until the
  // backend has actually marked the subscription active (same idea as /success).
  // Its own effect: clearing the URL above re-runs that one, and its cleanup
  // would otherwise cancel this poll immediately.
  useEffect(() => {
    if (subState !== "confirming") return;
    let cancelled = false;
    (async () => {
      for (let i = 0; i < 10; i++) {
        try {
          const u = await me();
          if (cancelled) return;
          if (u.subscription_status === "active") return setSubState("active");
        } catch {
          /* transient — retry */
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
      if (!cancelled) setSubState("slow");
    })();
    return () => {
      cancelled = true;
    };
  }, [subState]);

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
    <h2 className="mb-2 text-center text-[8px] font-medium uppercase tracking-[0.14em] text-zinc-500 sm:mb-3 sm:text-[10px] sm:tracking-[0.2em]">{text}</h2>
  );

  return (
    <div className="mx-auto w-full max-w-6xl px-3 text-left sm:px-4">
      <section className="py-5 text-center sm:py-9 ">
        <h1>
          <span className="text-[#d33a2c]">FIGHTS,</span> FIGURED OUT.
        </h1>
        {subState && <SubscribedPanel state={subState} onClose={() => setSubState(null)} />}
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
        <aside className="flex flex-col gap-5 sm:gap-6 lg:w-80 lg:shrink-0">
          {/* the advert: its record on past fights, above Dream fights */}
          <BoutBrainRecord heading={heading("The record")} />
          <div>
          {heading("Dream fights")}
          <DreamFights
            paywalled={paywalled}
            onFreeLeft={setFreeLeft}
            onPaywall={() => setPaywalled(true)}
          />
          </div>
        </aside>
      </section>
    </div>
  );
}

// Pull a readable message out of an unknown caught error.
function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}
