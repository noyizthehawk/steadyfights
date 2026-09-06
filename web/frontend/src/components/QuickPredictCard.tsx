import { useState } from "react";
import { predict, PaywallError } from "../api";
import type { Bout, PredictResult } from "../api";

// Same red/blue convention as ResultCard: fighter A red, fighter B blue, held
// consistently across image glow, name and result bar. Kept as full literal
// strings because Tailwind scans source and won't generate assembled classes.
const A = { name: "text-[#d33a2c]", bar: "bg-[#d33a2c]", glow: "from-[#d33a2c]/25" };
const B = { name: "text-blue-400", bar: "bg-blue-400", glow: "from-blue-400/25" };

type Props = {
  fight: Bout;
  /** names the model knows — a fight with an unseen fighter can't be predicted */
  known: Set<string>;
  /** locked out until they subscribe */
  paywalled: boolean;
  onFreeLeft: (n: number | null) => void;
  onPaywall: () => void;
};

export function QuickPredictCard({ fight, known, paywalled, onFreeLeft, onPaywall }: Props) {
  const [result, setResult] = useState<PredictResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  const predictable = known.has(fight.fighter_a) && known.has(fight.fighter_b);
  const pickedA = result?.pick === fight.fighter_a;

  async function run() {
    setError("");
    setLoading(true);
    try {
      const data = await predict(fight.fighter_a, fight.fighter_b);
      setResult(data);
      onFreeLeft(data.free_remaining);
    } catch (e: unknown) {
      if (e instanceof PaywallError) onPaywall();
      else setError(e instanceof Error ? e.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }

  const fighter = (name: string, img: string | null, c: typeof A, align: string) => (
    <div className="relative flex min-w-0 flex-1 flex-col items-center">
      {/* the ufc.com asset is a transparent waist-up PNG, so object-bottom stands
          the fighter on the baseline and the glow reads as a floor light */}
      <div className={`relative flex h-28 w-full items-end justify-center overflow-hidden rounded-lg bg-gradient-to-t ${c.glow} to-transparent sm:h-32`}>
        {img ? (
          <img src={img} alt={name} loading="lazy" className="h-full w-full object-contain object-bottom" />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[10px] text-zinc-600">no image</div>
        )}
      </div>
      <div className={`mt-2 w-full truncate px-1 font-display text-[10px] uppercase max-sm:text-[8px] ${c.name} ${align}`}>
        {name}
      </div>
    </div>
  );

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-700 bg-black">
      <div className="flex items-end gap-1 px-2 pt-2">
        {fighter(fight.fighter_a, fight.img_a, A, "text-left")}
        <span className="shrink-0 pb-8 font-display text-[10px] text-white max-sm:text-[8px]">VS</span>
        {fighter(fight.fighter_b, fight.img_b, B, "text-right")}
      </div>

      <div className="px-3 pb-3 pt-2.5">
        {result ? (
          <>
            <div className="flex h-2 w-full overflow-hidden bg-zinc-800">
              <div className={A.bar} style={{ width: `${result.prob_a}%` }} />
              <div className={B.bar} style={{ width: `${result.prob_b}%` }} />
            </div>
            <div className="mt-1.5 flex justify-between font-display text-[9px] max-sm:text-[8px]">
              <span className={A.name}>{result.prob_a}%</span>
              <span className={B.name}>{result.prob_b}%</span>
            </div>
            <div className="mt-2 border-t border-zinc-800 pt-2">
              <div className="text-[9px] uppercase tracking-widest text-zinc-500">SteadyIQ pick</div>
              <div className="mt-1 flex items-baseline justify-between gap-2">
                <span className={`truncate font-display text-[10px] ${pickedA ? A.name : B.name}`}>
                  {result.pick}
                </span>
                <span className="shrink-0 text-[10px] tabular-nums text-zinc-400">
                  {result.confidence}%
                </span>
              </div>
            </div>
          </>
        ) : !predictable ? (
          <div className="rounded-lg border border-zinc-800 py-2 text-center text-[10px] leading-tight text-zinc-500">
            No model data
          </div>
        ) : paywalled ? (
          // the subscribe CTA already sits at the top of the page; a dead
          // button here would just be a second thing that does nothing
          <div className="rounded-lg border border-zinc-800 py-2 text-center text-[10px] leading-tight text-zinc-500">
            Out of free predictions
          </div>
        ) : (
          <button
            className="w-full cursor-pointer rounded-lg bg-[#d33a2c] py-2 font-display text-[10px] text-white transition-opacity hover:opacity-90 disabled:cursor-default disabled:opacity-50 max-sm:text-[8px]"
            onClick={run}
            disabled={loading}
          >
            {loading ? "…" : "Predict"}
          </button>
        )}
        {error && <p className="mt-1.5 text-[10px] leading-tight text-red-400">{error}</p>}
      </div>
    </div>
  );
}
