import type { CareerSummary } from "../api";

// Card 1: fighter details / tale of the tape — the standing image, physicals
// (height, reach, stance) and the UFCStats striking + grappling rates.
export function FighterDetailsCard({ summary }: { summary: CareerSummary }) {
    const t = summary.tale_of_the_tape;
    const pct = (v: number | null | undefined) => (v != null ? `${v}%` : "—");
    const num = (v: number | null | undefined) => (v != null ? String(v) : "—");

    const rows: [string, string][] = [
        ["Height", t?.height_cm != null ? `${t.height_cm} cm` : "—"],
        ["Reach", t?.reach_cm != null ? `${t.reach_cm} cm` : "—"],
        ["Stance", t?.stance ?? "—"],
        ["Sig. strike accuracy", pct(t?.str_acc)],
        ["Sig. strike defense", pct(t?.str_def)],
        ["Strikes landed / min", num(t?.slpm)],
        ["Strikes absorbed / min", num(t?.sapm)],
        ["Takedown accuracy", pct(t?.td_acc)],
        ["Takedown defense", pct(t?.td_def)],
        ["Takedowns / 15 min", num(t?.td_avg)],
        ["Sub attempts / 15 min", num(t?.sub_avg)],
    ];

    return (
        <div className="relative border border-zinc-700 rounded-lg p-4">
            <div className="profile-header">
                <div className="flex flex-wrap items-baseline gap-x-2.5">
                    <h2 className="text-xl font-bold text-white sm:text-2xl">{summary.fighter}</h2>
                </div>
            </div>

            <div className="mt-3 divide-y divide-zinc-800">
                {rows.map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between py-1.5 text-sm">
                        <span className="text-zinc-400">{label}</span>
                        <span className="font-semibold tabular-nums text-white">{value}</span>
                    </div>
                ))}
            </div>

            {!t && (
                <p className="mt-2 text-xs text-zinc-500">Detailed stats unavailable for this fighter.</p>
            )}
        </div>
    );
}
