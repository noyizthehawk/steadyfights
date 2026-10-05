import type { CareerSummary } from "../api";
import { Bar, Figure } from "./Meters";

/** p2-p98 of each stat, measured over fighters with 5+ UFC bouts.
 *
 *  The point of the bar is to show where someone sits IN THE DATA, so every
 *  bound is measured rather than chosen. Two decisions behind that:
 *
 *  p2-p98, not the tighter p10-p90 these started on. At p90 the top of striking
 *  accuracy was 54%, so a genuinely very good 57% filled the track completely
 *  and read as perfect — and 29 fighters with real careers, Aspinall at 67%
 *  among them, were indistinguishable. Only the outer 2% clamp now.
 *
 *  And 5+ bouts, not everyone. A fighter who went 1-for-1 on takedowns shows
 *  100% accuracy; 22 of those sat at the top of the unrestricted distribution
 *  and would have set the ceiling for the whole roster. Five fights is enough
 *  that a rate means something.
 *
 *  Percentages are deliberately not scaled 0-100: nobody lands 0% or 100% of
 *  their strikes, so a raw percentage bar sits mid-track for everyone and
 *  separates nothing.
 */
const SCALE: Record<string, [number, number]> = {
    str_acc: [31, 61],
    str_def: [39, 68],
    slpm: [1.3, 6.4],
    sapm: [1.5, 6.3],
    td_acc: [14, 81],
    td_def: [23, 100],
    td_avg: [0.2, 5.1],
    sub_avg: [0.1, 2.6],
};

/** Where a value sits in its own range, as a 0-100 figure the Bar can take. */
function scaled(value: number | null | undefined, key: string, invert = false): number | null {
    if (value == null) return null;
    const [low, high] = SCALE[key];
    const t = (value - low) / (high - low);
    // Absorbing fewer strikes is better, so its bar has to fill the other way
    // or a durable fighter would read as the worst on the card.
    return Math.max(0, Math.min(100, (invert ? 1 - t : t) * 100));
}

function StatBar({
    label,
    value,
    display,
    statKey,
    invert,
}: {
    label: string;
    value: number | null | undefined;
    display: string;
    statKey: string;
    invert?: boolean;
}) {
    return (
        <div>
            <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="text-[10px] font-medium text-zinc-400">{label}</span>
                <span className="text-[11px] font-bold tabular-nums text-white">{display}</span>
            </div>
            {/* The bar carries the comparison, the number carries the fact. A
                reader who only wants "is this good" gets it from the fill. */}
            <Bar value={scaled(value, statKey, invert)} label="" max={100} showHeader={false} />
        </div>
    );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="rounded-xl bg-white/[0.035] p-3">
            <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                {title}
            </h3>
            <div className="space-y-2.5">{children}</div>
        </div>
    );
}

// Card 1: fighter details / tale of the tape — physicals (height, reach,
// stance) and the UFCStats striking + grappling rates.
export function FighterDetailsCard({ summary }: { summary: CareerSummary }) {
    const t = summary.tale_of_the_tape;
    const pct = (v: number | null | undefined) => (v != null ? `${v}%` : "—");
    const num = (v: number | null | undefined) => (v != null ? String(v) : "—");

    return (
        <div className="relative rounded-lg border border-zinc-700 p-4 text-left">
            <h2 className="text-xl font-bold text-white sm:text-2xl">{summary.fighter}</h2>

            {!t ? (
                <p className="mt-3 text-xs text-zinc-500">
                    Detailed stats unavailable for this fighter.
                </p>
            ) : (
                <div className="mt-3 space-y-2">
                    {/* Physicals are facts with no scale — a 180cm fighter is not
                        "better" than a 175cm one — so they get plain figures. Only
                        the rate stats, where more or less genuinely is better, earn
                        a meter. */}
                    <div className="grid grid-cols-3 gap-2">
                        <Figure value={t.height_cm != null ? `${t.height_cm}` : "—"} label="Height (cm)" />
                        <Figure value={t.reach_cm != null ? `${t.reach_cm}` : "—"} label="Reach (cm)" />
                        <Figure value={t.stance ?? "—"} label="Stance" />
                    </div>

                    <div className="grid gap-2 sm:grid-cols-2">
                        <Group title="Striking">
                            <StatBar label="Accuracy" value={t.str_acc} display={pct(t.str_acc)} statKey="str_acc" />
                            <StatBar label="Defense" value={t.str_def} display={pct(t.str_def)} statKey="str_def" />
                            <StatBar label="Landed / min" value={t.slpm} display={num(t.slpm)} statKey="slpm" />
                            <StatBar label="Absorbed / min" value={t.sapm} display={num(t.sapm)} statKey="sapm" invert />
                        </Group>

                        <Group title="Grappling">
                            <StatBar label="Takedown accuracy" value={t.td_acc} display={pct(t.td_acc)} statKey="td_acc" />
                            <StatBar label="Takedown defense" value={t.td_def} display={pct(t.td_def)} statKey="td_def" />
                            <StatBar label="Takedowns / 15 min" value={t.td_avg} display={num(t.td_avg)} statKey="td_avg" />
                            <StatBar label="Sub attempts / 15 min" value={t.sub_avg} display={num(t.sub_avg)} statKey="sub_avg" />
                        </Group>
                    </div>
                </div>
            )}
        </div>
    );
}
