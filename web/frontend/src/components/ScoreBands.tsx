import type { ScoreBand } from "../api";

/** Below this many picks a band's rate is shown, but flagged as thin. */
const SMALL_SAMPLE = 30;

/** How Bout Brain's score has performed, band by band.
 *
 *  The selling point is the SHAPE: each step up the score is right more
 *  often, so the score means what it says — a 75 is worth more than a 55.
 *  Bars run from 0 to 100 with the coin-flip line at 50, so "better than a
 *  guess, and better the surer it is" reads at a glance. Every decided fight
 *  is counted, so the rows add up to the whole record — no hand-picked list.
 *
 *  `compact` is the sidebar version: no counts column, tighter rows. */
export function ScoreBands({ bands, compact = false }: { bands: ScoreBand[]; compact?: boolean }) {
  const shown = bands.filter((b) => b.accuracy !== null);
  if (shown.length === 0) return null;

  return (
    <div>
      {!compact && (
        <div className="mb-3 grid grid-cols-[3.5rem_1fr_6.5rem] gap-3 text-[10px] font-bold uppercase tracking-wider text-zinc-600">
          <span>Score</span>
          <span>Winner correct</span>
          <span className="text-right">Picks</span>
        </div>
      )}
      <ul className={`m-0 list-none p-0 ${compact ? "space-y-1.5" : "space-y-2.5"}`}>
        {shown.map((b) => {
          const thin = b.picks < SMALL_SAMPLE;
          return (
            <li
              key={b.label}
              className={`grid items-center gap-3 ${compact ? "grid-cols-[2.6rem_1fr_2.4rem]" : "grid-cols-[3.5rem_1fr_6.5rem]"}`}
              title={`Score ${b.label}: right ${b.correct} of ${b.picks} times${thin ? " (small sample)" : ""}`}
            >
              <span className={`font-mono tabular-nums text-zinc-400 ${compact ? "text-[10px]" : "text-xs"}`}>
                {b.label}
              </span>
              {/* 0-100 track; the tick at 50 is a coin flip */}
              <span className={`relative block overflow-hidden bg-zinc-800 ${compact ? "h-1.5" : "h-2.5"}`}>
                <span
                  className={`absolute inset-y-0 left-0 ${bandColour(b.accuracy!)} ${thin ? "opacity-50" : ""}`}
                  style={{ width: `${b.accuracy}%` }}
                />
                <span className="absolute inset-y-0 left-1/2 w-px bg-zinc-950/80" />
              </span>
              <span
                className={`text-right tabular-nums ${compact ? "text-[10px] text-zinc-300" : "text-xs text-zinc-200"}`}
              >
                <span className="font-bold">{Math.round(b.accuracy!)}%</span>
                {!compact && (
                  <span className="text-zinc-500">
                    {" "}
                    ({b.correct}/{b.picks})
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {/* honest about the thin end of the table */}
      {!compact && shown.some((b) => b.picks < SMALL_SAMPLE) && (
        <div className="mt-2 text-[10px] italic text-zinc-600" style={{ fontFamily: "var(--font-rundown)" }}>
        </div>
      )}
    </div>
  );
}

/** Climbs with the rate: grey near a coin flip, through amber, to green. */
function bandColour(accuracy: number): string {
  if (accuracy >= 75) return "bg-emerald-500";
  if (accuracy >= 65) return "bg-lime-500";
  if (accuracy >= 55) return "bg-amber-500";
  return "bg-zinc-500";
}

/** "56% → 67% → 79% → 100%": the climb in one line, for headlines. */
export function bandClimb(bands: ScoreBand[]): string {
  return bands
    .filter((b) => b.accuracy !== null)
    .map((b) => `${Math.round(b.accuracy!)}%`)
    .join(" → ");
}
