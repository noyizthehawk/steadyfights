import { useEffect, useState } from "react";
import { getDreamFighters, dreamFight, PaywallError } from "../api";
import type { CareerStage, DreamResult, StageMeta } from "../api";
import { ResultCard } from "./ResultCard";

const STAGES: CareerStage[] = ["Early", "Prime", "Late"];

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
          className={`cursor-pointer rounded-md py-1.5 text-[11px] font-medium transition-colors ${
            value === s ? "bg-[#d33a2c] text-white" : "text-zinc-400 hover:text-zinc-200"
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
        placeholder="Type a name…"
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-600 transition-colors focus:border-[#d33a2c] focus:outline-none"
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
function StageLine({ name, meta, align }: { name: string; meta: StageMeta; align: string }) {
  return (
    <div className={`min-w-0 flex-1 ${align}`}>
      <div className="truncate text-[11px] font-semibold uppercase tracking-wide text-white">
        {meta.stage} {name}
      </div>
      <div className="mt-0.5 truncate text-[10px] tabular-nums text-zinc-500">
        {meta.span} · {meta.fights} fights · age {meta.avg_age}
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
      <div className="rounded-xl border border-zinc-700 bg-black p-4">
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
          className="mt-5 w-full cursor-pointer rounded-lg bg-[#d33a2c] py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-default disabled:opacity-50"
          onClick={run}
          disabled={loading || paywalled}
        >
          {loading ? "Booking…" : paywalled ? "Out of free predictions" : "Book the fight"}
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
          <div className="mt-4 flex items-start gap-3 rounded-xl border border-zinc-800 bg-black px-4 py-3">
            <StageLine name={result.fighter_a} meta={result.stage_a} align="text-left" />
            <StageLine name={result.fighter_b} meta={result.stage_b} align="text-right" />
          </div>
          <ResultCard result={result} />
        </>
      )}
    </section>
  );
}
