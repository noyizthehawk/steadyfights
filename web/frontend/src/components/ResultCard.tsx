import type { PredictResult } from "../api";

const A = { name: "text-[#d33a2c]", bar: "bg-[#d33a2c]", pick: "border-[#d33a2c]/50 bg-[#d33a2c]/10" };
const B = { name: "text-blue-400", bar: "bg-blue-400", pick: "border-blue-400/50 bg-blue-400/10" };

const LABEL = "text-[9px] uppercase tracking-widest text-zinc-500";

export function ResultCard({ result }: { result: PredictResult }) {
  const pickedA = result.pick === result.fighter_a;
  const picked = pickedA ? A : B;

  return (
    <div className="mx-auto mt-6 h-fit w-full max-w-xl overflow-hidden rounded-xl border border-zinc-700 bg-black text-left">
      
      <div className="flex items-start justify-between gap-3 px-4 pt-4 sm:px-5">
        <div className="min-w-0 flex-1">
          <h3 className={`truncate font-display uppercase text-sm max-sm:text-[11px] ${A.name}`}>
            {result.fighter_a}
          </h3>
          <div className="mt-1 truncate text-xs text-zinc-400">{result.style_a}</div>
        </div>
        <span className="shrink-0 pt-1 font-display text-[10px] text-white max-sm:text-[8px]">VS</span>
        <div className="min-w-0 flex-1 text-right">
          <h3 className={`truncate font-display uppercase text-sm max-sm:text-[11px] ${B.name}`}>
            {result.fighter_b}
          </h3>
          <div className="mt-1 truncate text-xs text-zinc-400">{result.style_b}</div>
        </div>
      </div>

      {/* One bar, not two: the probabilities sum to 100, so a single split track
          shows the gap directly. Square edges, not rounded-full -- reads as a
          pixel meter rather than a progress bar. */}
      <div className="mt-3 flex h-2.5 w-full overflow-hidden bg-zinc-800">
        <div className={`${A.bar} transition-[width] duration-500 ease-out`} style={{ width: `${result.prob_a}%` }} />
        <div className={`${B.bar} transition-[width] duration-500 ease-out`} style={{ width: `${result.prob_b}%` }} />
      </div>
      <div className="flex justify-between px-4 pt-1.5 font-display text-[11px] max-sm:text-[9px] sm:px-5">
        <span className={A.name}>{result.prob_a}%</span>
        <span className={B.name}>{result.prob_b}%</span>
      </div>

      {/* The headline. ▶ borrows the room-card cursor motif, but static: that
          blink is scoped to `.group:hover` in rooms.css and there is nothing to
          hover here. */}
      <div className="px-4 pt-4 sm:px-5">
        <div className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 ${picked.pick}`}>
          <span aria-hidden className={`shrink-0 font-display text-[10px] ${picked.name}`}>
            ▶
          </span>
          <div className="min-w-0 flex-1">
            <div className={LABEL}>STEADYIQ PICK</div>
            <div className={`mt-1 truncate font-display text-xs max-sm:text-[10px] ${picked.name}`}>
              {result.pick}
            </div>
          </div>
          <div className="shrink-0 text-right">
            <div className={LABEL}>Conf</div>
            <div className="mt-1 font-display text-xs tabular-nums text-zinc-300 max-sm:text-[10px]">
              {result.confidence}%
            </div>
          </div>
        </div>
      </div>

      {/* Score-table readout, same single-line-per-stat language as RoomCard. */}
      <div className="mt-4 border-t border-zinc-800 px-4 py-3 sm:px-5">
        <div className={`${LABEL} mb-1`}>Tale of the tape</div>
        <div className="divide-y divide-zinc-800/70">
          {result.factors.map((f) => (
            <div key={f.label} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 py-2">
              {/* the fighter who wins this stat gets their colour; the other stays muted */}
              <span
                className={`text-left text-sm tabular-nums ${
                  f.favors === result.fighter_a ? `font-semibold ${A.name}` : "text-zinc-400"
                }`}
              >
                {f.value_a}
              </span>
              <span className="text-center text-[10px] uppercase tracking-wider leading-tight text-zinc-500">
                {f.label}
              </span>
              <span
                className={`text-right text-sm tabular-nums ${
                  f.favors === result.fighter_b ? `font-semibold ${B.name}` : "text-zinc-400"
                }`}
              >
                {f.value_b}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
