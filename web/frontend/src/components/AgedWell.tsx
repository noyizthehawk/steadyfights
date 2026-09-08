import { Link } from "react-router-dom";
import type { AgedWell as AgedWellRow } from "../api";

// The strength score on a fighter's card is what the opponent was worth ON THE
// NIGHT. That hides the two most interesting things a result can do with time:
// beating someone before anyone knew who they were, or losing to someone who
// went on to take a belt.
//
// Only gains AFTER the fight qualify. An all-time peak would rate Adesanya
// beating a 2019 Anderson Silva (peak 2012) the same as Usman beating a 2015
// Leon Edwards (champion 2022), which are opposite stories.

// same gold as the coin icon and the Ask Dana button
const GOLD = "#ffd75e";

export function AgedWell({ rows, fighter }: { rows: AgedWellRow[]; fighter: string }) {
  if (!rows || rows.length === 0) return null;

  return (
    <section className="rounded-lg border border-zinc-700 p-4 text-left">
      <h2 className="mb-1 text-[9px] font-medium uppercase tracking-[0.2em] text-zinc-500">
        Aged well
      </h2>
      <p className="mb-3 text-[11px] leading-snug text-zinc-400">
        What {fighter.split(" ")[0]}'s opponents went on to become after they met.
      </p>

      <table className="w-full border-collapse text-[11px]">
        <thead>
          <tr className="text-[9px] uppercase tracking-widest text-zinc-500">
            <th className="pb-1.5 text-left font-medium">Opponent</th>
            <th className="pb-1.5 text-right font-medium">Then</th>
            <th className="pb-1.5 text-right font-medium">Peak</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {rows.map((r) => {
            const gain = r.peak_after !== null ? Math.round((r.peak_after - r.then) * 100) : 0;
            return (
              <tr key={`${r.fight_number}-${r.opponent}`} className="align-top">
                <td className="py-2 pr-2">
                  <div className="flex min-w-0 items-center gap-1.5">
                    {/* W/L first: the same rise means opposite things depending on it */}
                    <span
                      className={`shrink-0 text-[10px] font-bold ${
                        r.won ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      {r.won ? "W" : "L"}
                    </span>
                    <Link
                      to={`/fighters/${encodeURIComponent(r.opponent)}/career`}
                      className="truncate text-white underline-offset-2 hover:text-zinc-400 hover:underline"
                    >
                      {r.opponent}
                    </Link>
                  </div>
                  {r.became_champion && (
                    <span
                      className="mt-1 inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide"
                      style={{ color: GOLD, background: `${GOLD}1a`, boxShadow: `inset 0 0 0 1px ${GOLD}44` }}
                    >
                      ★ Champion
                      <span className="font-normal opacity-70">
                        {r.champion_years_later === null
                          ? "in this fight"
                          : `${r.champion_years_later}y later`}
                      </span>
                    </span>
                  )}
                </td>
                <td className="py-2 text-right tabular-nums text-zinc-400">
                  {Math.round(r.then * 100)}
                </td>
                <td className="py-2 text-right tabular-nums">
                  {r.peak_after === null ? (
                    <span className="text-zinc-600">—</span>
                  ) : (
                    <>
                      <span className="text-white">{Math.round(r.peak_after * 100)}</span>
                      {gain > 0 && <span className="text-[10px] text-green-500"> +{gain}</span>}
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="mt-3 text-[10px] leading-snug text-zinc-500">
        Opponent strength on the night vs the best they reached afterwards, out of 75.
      </p>
    </section>
  );
}
