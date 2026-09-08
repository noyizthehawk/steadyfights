import { useState } from "react";
import type { TimelineFight } from "../api";

// Two things move over a career: how well the fighter performs, and how hard the
// opposition gets. The story is in the gap between them —
//
//                        opposition rising     opposition flat
//   performance holding  levelling up          padding the record
//   performance falling  out of their depth    declining
//
// which is a claim the win/loss record can't make on its own.

const PERF = "#d33a2c";
const OPP = "#60a5fa";

const W = 320;   // viewBox units; the svg scales to its container
const H = 120;
const PAD = { top: 8, right: 6, bottom: 18, left: 6 };

// Per-fight scores swing hard on a finish vs a decision, so the lines are a
// 3-fight trailing mean. The dots stay raw — that's where the individual
// opponents live, and smoothing them away would defeat the point.
function smooth(vals: number[], k = 3): number[] {
  return vals.map((_, i) => {
    const win = vals.slice(Math.max(0, i - k + 1), i + 1);
    return win.reduce((a, b) => a + b, 0) / win.length;
  });
}

export function CareerChart({ timeline }: { timeline: TimelineFight[] }) {
  const [sel, setSel] = useState<number | null>(null);

  // two fights is a line segment, not a trend. The null check is not paranoia:
  // during a deploy the frontend can be live before the backend, and an older
  // API response has no `timeline` at all — reading .length off undefined threw
  // and blanked the whole page.
  if (!timeline || timeline.length < 3) return null;

  const n = timeline.length;
  const perf = timeline.map((f) => f.perf);
  const opp = timeline.map((f) => f.opp);

  // Fixed domains, not per-fighter min/max: auto-scaling would make every
  // fighter's chart look equally dramatic and stop them being comparable.
  const px = (i: number) => PAD.left + (i / Math.max(1, n - 1)) * (W - PAD.left - PAD.right);
  const yPerf = (v: number) =>
    PAD.top + (1 - Math.min(1, Math.max(0, (v - 20) / 60))) * (H - PAD.top - PAD.bottom);
  const yOpp = (v: number) =>
    PAD.top + (1 - Math.min(1, Math.max(0, (v - 0.4) / 0.4))) * (H - PAD.top - PAD.bottom);

  const line = (vals: number[], y: (v: number) => number) =>
    smooth(vals).map((v, i) => `${i ? "L" : "M"}${px(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  const active = sel !== null ? timeline[sel] : null;

  return (
    <div className="rounded-lg border border-zinc-700 p-4 text-left">
      <h2 className="mb-1 text-[9px] font-medium uppercase tracking-[0.2em] text-zinc-500">
        Career trajectory
      </h2>
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px]">
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded" style={{ background: PERF }} />
          <span className="text-zinc-400">Performance</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-4 rounded" style={{ background: OPP }} />
          <span className="text-zinc-400">Opponent strength</span>
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
           aria-label={`Performance and opponent strength across ${n} fights`}>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={PAD.left} x2={W - PAD.right}
                y1={PAD.top + f * (H - PAD.top - PAD.bottom)}
                y2={PAD.top + f * (H - PAD.top - PAD.bottom)}
                stroke="#27272a" strokeWidth="0.5" />
        ))}

        <path d={line(opp, yOpp)} fill="none" stroke={OPP} strokeWidth="1.5"
              strokeLinejoin="round" opacity="0.9" />
        <path d={line(perf, yPerf)} fill="none" stroke={PERF} strokeWidth="1.5"
              strokeLinejoin="round" />

        {/* One dot per fight — the individual opponents. A loss is hollow, so the
            shape carries the result and colour stays free for the series. */}
        {timeline.map((f, i) => (
          <g key={f.fight_number}>
            <circle cx={px(i)} cy={yOpp(f.opp)} r={sel === i ? 3 : 2}
                    fill={f.won ? OPP : "#0a0a0a"} stroke={OPP} strokeWidth="1" />
            <circle cx={px(i)} cy={yPerf(f.perf)} r={sel === i ? 3 : 2}
                    fill={f.won ? PERF : "#0a0a0a"} stroke={PERF} strokeWidth="1" />
            {/* generous invisible hit area — the dots are far too small to tap */}
            <rect x={px(i) - (W / n) / 2} y="0" width={W / n} height={H}
                  fill="transparent" className="cursor-pointer"
                  onMouseEnter={() => setSel(i)} onClick={() => setSel(i)}>
              <title>{`${f.won ? "W" : "L"} vs ${f.opponent}`}</title>
            </rect>
          </g>
        ))}

        {sel !== null && (
          <line x1={px(sel)} x2={px(sel)} y1={PAD.top} y2={H - PAD.bottom}
                stroke="#52525b" strokeWidth="0.5" strokeDasharray="2 2" />
        )}

        <text x={PAD.left} y={H - 4} fill="#52525b" fontSize="7">fight 1</text>
        <text x={W - PAD.right} y={H - 4} fill="#52525b" fontSize="7" textAnchor="end">
          fight {n}
        </text>
      </svg>

      {/* Fixed height so selecting a fight doesn't shift the page under the cursor */}
      <div className="mt-2 flex min-h-[34px] items-center border-t border-zinc-800 pt-2 text-[11px]">
        {active ? (
          <div className="min-w-0">
            <span className={`font-semibold ${active.won ? "text-green-500" : "text-red-500"}`}>
              {active.won ? "W" : "L"}
            </span>
            <span className="text-white"> vs {active.opponent}</span>
            <span className="text-zinc-500">
              {" · "}perf {active.perf} / 75 · opp {Math.round(active.opp * 100)} / 75
            </span>
          </div>
        ) : (
          <span className="text-zinc-500">Hover or tap a fight for the opponent</span>
        )}
      </div>
    </div>
  );
}
