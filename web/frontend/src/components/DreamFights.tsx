import { useEffect, useState } from "react";
import { getDreamFighters, dreamFight, PaywallError } from "../api";
import type { CareerStage, DreamResult, StageMeta } from "../api";
import { ResultCard } from "./ResultCard";

const STAGES: CareerStage[] = ["Early", "Prime", "Late"];

// One colour per stage rather than a single "selected" fill, so the choice is
// readable at a glance without reading the labels. Each is dark or light enough
// to carry its own label colour at 4.5:1+.
const STAGE_ON: Record<CareerStage, string> = {
  Early: "bg-blue-400 text-zinc-900",
  Prime: "bg-[#d33a2c] text-white",
  Late: "bg-[#4ade80] text-zinc-900",
};

type Props = {
  paywalled: boolean;
  onFreeLeft: (n: number | null) => void;
  onPaywall: () => void;
};

// iOS-style segmented control: one recessed track with the active segment
// raised out of it. Reads cleaner in a narrow column than three outlined
// buttons, and the body font stays legible at 11px where the pixel font can't.
function StagePicker({
  value, onChange, name,
}: { value: CareerStage; onChange: (s: CareerStage) => void; name: string }) {
  return (
    <div
      className="mt-2 grid grid-cols-3 gap-0.5 rounded-lg bg-zinc-900 p-0.5"
      role="group"
      aria-label={`${name} career stage`}
    >
      {STAGES.map((s) => (
        <button
          key={s}
          type="button"
          aria-pressed={value === s}
          onClick={() => onChange(s)}
          className={`min-h-[34px] cursor-pointer rounded-md text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400/60 ${
            value === s ? STAGE_ON[s] : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
          }`}
        >
          {s}
        </button>
      ))}
    </div>
  );
}

function FighterPicker({
  label, value, onChange, stage, onStage, options,
}: {
  label: string; value: string; onChange: (v: string) => void;
  stage: CareerStage; onStage: (s: CareerStage) => void; options: string[];
}) {
  const listId = `dream-${label.replace(/\s+/g, "-")}`;
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-widest text-zinc-500">{label}</label>
      <input
        type="text"
        list={listId}
        value={value}
        placeholder="..."
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 min-h-[44px] w-full rounded-lg border border-zinc-800 bg-[#0c0d11] px-3 text-base text-white placeholder-zinc-600 transition-colors hover:border-zinc-700 focus:border-[#d33a2c] focus:outline-none focus:ring-[3px] focus:ring-[#d33a2c]/20"
      />
      <datalist id={listId}>
        {options.map((n) => <option key={n} value={n} />)}
      </datalist>
      <StagePicker value={stage} onChange={onStage} name={label} />
    </div>
  );
}

// What the model averaged to build this version of the fighter — shown so
// "Prime" is visibly a span of real bouts rather than a label we assert, and so
// Anderson Silva's prime reading age 36 explains itself.
function StageLine({ name, meta, accent }: { name: string; meta: StageMeta; accent: string }) {
  return (
    <div>
      <div className={`text-[11px] font-semibold uppercase tracking-wide ${accent}`}>
        {meta.stage} {name}
      </div>
      <div className="mt-0.5 text-[10px] leading-snug tabular-nums text-zinc-500">
        {meta.span} · {meta.fights} fights · avg age {meta.avg_age}
      </div>
    </div>
  );
}

export function DreamFights({ paywalled, onFreeLeft, onPaywall }: Props) {
  const [fighters, setFighters] = useState<string[]>([]);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [stageA, setStageA] = useState<CareerStage>("Prime");
  const [stageB, setStageB] = useState<CareerStage>("Prime");
  const [result, setResult] = useState<DreamResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getDreamFighters().then(setFighters).catch(() => setError("Couldn't load fighters."));
  }, []);

  async function run() {
    setError("");
    setResult(null);
    if (!a || !b) return setError("Pick both fighters.");
    setLoading(true);
    try {
      const data = await dreamFight(a, stageA, b, stageB);
      setResult(data);
      onFreeLeft(data.free_remaining);
    } catch (e: unknown) {
      if (e instanceof PaywallError) onPaywall();
      else setError(e instanceof Error ? e.message : "Dream fight failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="w-full text-left">
      <div className="rounded-xl border border-zinc-800 bg-black p-3.5 sm:p-4">
        <p className="text-xs leading-snug text-zinc-400">
          Any two fighters, at any point in their careers.
        </p>

        <div className="mt-4 space-y-4">
          <FighterPicker label="Fighter A" value={a} onChange={setA}
                         stage={stageA} onStage={setStageA} options={fighters} />

          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-zinc-800" />
            <span className="font-display text-[9px] text-zinc-500">VS</span>
            <span className="h-px flex-1 bg-zinc-800" />
          </div>

          <FighterPicker label="Fighter B" value={b} onChange={setB}
                         stage={stageB} onStage={setStageB} options={fighters} />
        </div>

        <button
          className="mt-5 min-h-[44px] w-full cursor-pointer rounded-lg bg-[#ffd75e] text-sm font-semibold text-[#17140a] transition-[background-color,transform] duration-150 hover:bg-[#ffe694] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ffe694] focus-visible:ring-offset-2 focus-visible:ring-offset-black active:scale-[0.99] disabled:cursor-default disabled:opacity-50"
          onClick={run}
          disabled={loading || paywalled}
        >
          {loading ? "Booking…" : paywalled ? "Out of free predictions" : "Ask Dana!"}
        </button>

        {/* A fighter's prime is not always mid-career — Anderson Silva's runs
            2009-2012, ages 32-36. The spans on each result show this, but say
            it out loud too. */}
        <p className="mt-3 text-[10px] leading-snug text-zinc-500">
          Stages are thirds of each fighter's UFC career, averaged. Some peak
          late career, so a "Late" career can be their best.
        </p>

        {error && <p className="mt-2 text-[11px] text-red-400">{error}</p>}
      </div>

      {result && (
        <>
          <div className="mt-4 space-y-2.5 rounded-xl border border-zinc-800 bg-black px-3.5 py-3">
            <StageLine name={result.fighter_a} meta={result.stage_a} accent="text-[#d33a2c]" />
            <div className="h-px bg-zinc-800" />
            <StageLine name={result.fighter_b} meta={result.stage_b} accent="text-blue-400" />
          </div>
          <ResultCard result={result} />
        </>
      )}
    </section>
  );
}
