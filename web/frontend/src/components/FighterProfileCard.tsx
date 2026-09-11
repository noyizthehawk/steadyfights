import type { CareerSummary, Phase } from "../api";
import { useState } from "react";
import { NewsList } from "./NewsList";

// Card 2: career statistics (performance IQ, form, phases, news). Receives the
// already-fetched summary from the page so both cards share one request.
export function FighterProfileCard({ summary }: { summary: CareerSummary }) {
    const [tab, setTab] = useState<"career" | "news">("career");
    // title of the expanded phase, or null. One at a time: the panel renders
    // below the row, so two open at once would have nowhere to go.
    const [openPhase, setOpenPhase] = useState<string | null>(null);

    // filter out phases the fighter never reached (a 4-fight career has no mid)
    const phaseList = ([
        ["Early (1–5)", summary.phases.early],
        ["Mid (6–10)", summary.phases.mid],
        ["Late (11+)", summary.phases.late],
    ] as [string, Phase | undefined][]).filter((e): e is [string, Phase] => Boolean(e[1]));
    const open = phaseList.find(([title]) => title === openPhase);

    return (
        <div className="relative rounded-lg border border-zinc-700 p-4 text-left">
            <div className="profile-header">
                <div className="flex min-w-0 flex-wrap items-baseline gap-x-2.5 gap-y-1">
                    <h2 className="text-xl font-bold text-white sm:text-2xl">{summary.fighter}</h2>
                    <span className="whitespace-nowrap text-xl font-bold tabular-nums text-red-500 sm:text-2xl">{summary.record}</span>
                    <ActivityChip activity={summary.activity} />
                </div>
                <div className="flex shrink-0 items-center gap-2">
                    <span className="career-score" title="Career quality (0–100)">
                        {summary.career_score}
                    </span>
                    {/* ufc.com serves a waist-up standing cutout, not a headshot, so
                        object-top is what actually frames the face. The PNGs are
                        transparent, hence the fill behind them or the circle vanishes. */}
                    {summary.image_url && (
                        <img
                            src={summary.image_url}
                            alt={summary.fighter}
                            loading="lazy"
                            className="h-12 w-12 shrink-0 rounded-full bg-zinc-800 object-cover object-top ring-1 ring-zinc-700 sm:h-14 sm:w-14"
                        />
                    )}
                </div>
            </div>

            <div className="tabs">
                <button
                    className={tab === "career" ? "tab active" : "tab"}
                    onClick={() => setTab("career")}
                >
                    Career
                </button>
                <button
                    className={tab === "news" ? "tab active" : "tab"}
                    onClick={() => setTab("news")}
                >
                    News
                </button>
            </div>

            {tab === "career" && (
                <>
                    <p className="career-label">{summary.career_label}</p>
                    {summary.trajectory && <p className="trajectory">{summary.trajectory}</p>}

                    <div className="career-stats">
                        <Stat label="Fights" value={summary.total_fights} />
                        <Stat label="Win rate" value={`${summary.win_rate}%`} />
                        <Stat label="SteadyPerformanceIQ" value={summary.avg_adj_perf} hint={summary.perf_label} />
                        <Stat label="Recent Form (L5)" value={summary.recent_perf} hint={`${summary.recent_record} last 5`} hintClass="text-green-500" />
                        <Stat label="SteadyStrengthIQ" value={summary.avg_opp_strength} hint={summary.opp_label} />
                        <Stat label="Volatility" value={summary.volatility} hint={summary.volatility_label} />
                    </div>

                    <div className="career-phases">
                        {phaseList.map(([title, phase]) => (
                            <PhaseColumn
                                key={title}
                                title={title}
                                phase={phase}
                                isOpen={openPhase === title}
                                onToggle={() => setOpenPhase((o) => (o === title ? null : title))}
                            />
                        ))}
                    </div>

                    {/* Expands in place below the row rather than floating over the
                        page. Sits outside .career-phases so it spans the full card
                        instead of being trapped in one grid column on desktop. */}
                    {open && (
                        <div
                            id="phase-bouts"
                            className="mt-3 rounded-lg border border-[#4ade80]/40 bg-[#0d0d0d] p-3"
                        >
                            <div className="mb-2 flex items-baseline justify-between gap-3">
                                <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[#4ade80]">
                                    {open[0]}
                                </h4>
                                <span className="shrink-0 text-[10px] tabular-nums text-zinc-500">
                                    {open[1].bouts.length} fight{open[1].bouts.length === 1 ? "" : "s"}
                                </span>
                            </div>
                            <ul className="max-h-72 space-y-1 overflow-y-auto pr-1">
                                {open[1].bouts.map((b) => (
                                    <li key={b.fight_number} className="flex items-center gap-2 text-xs">
                                        <span className={`w-6 shrink-0 rounded-md py-0.5 text-center font-bold text-white ${b.won ? "bg-green-500" : "bg-red-500"}`}>
                                            {b.won ? "W" : "L"}
                                        </span>
                                        <span className="min-w-0 flex-1 truncate">
                                            <a href={`/fighters/${encodeURIComponent(b.opponent)}/career`} className="text-white hover:text-zinc-400 hover:underline">
                                                {b.opponent}
                                            </a>{" "}
                                            <span className="text-zinc-500">({b.event})</span>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </>
            )}

            {tab === "news" && <NewsList fighter={summary.fighter} />}

        </div>
    );
}

// Deliberately neutral (zinc, not red/green): being retired isn't good or bad,
// it's context for why the trajectory line is in the past tense. Active fighters
// get nothing — the absence is the signal, and a chip on every page is noise.
function ActivityChip({ activity }: { activity: CareerSummary["activity"] }) {
    if (!activity || activity.status === "active" || activity.status === "unknown") return null;
    const retired = activity.status === "retired";
    const detail = retired
        ? (activity.last_fight ?? "").slice(0, 4)
        : activity.years_since !== null
            ? `${activity.years_since}y out`
            : "";
    return (
        <span className="inline-flex shrink-0 items-center gap-1 self-center rounded border border-zinc-700 bg-zinc-800/60 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-widest text-zinc-400">
            {retired ? "Retired" : "Inactive"}
            {detail && <span className="font-normal text-zinc-500">{detail}</span>}
        </span>
    );
}

function Stat({ label, value, hint, hintClass = "text-[#d33a2c]" }: { label: string; value: string | number; hint?: string; hintClass?: string }) {
    return (
        <div className="stat">
            <span className="stat-value">{value}</span>
            <span className="stat-label">{label}</span>
            {hint && <span className={`stat-hint text-xs ${hintClass}`}>{hint}</span>}
        </div>
    );
}

function PhaseColumn({
    title,
    phase,
    isOpen,
    onToggle,
}: {
    title: string;
    phase: Phase;
    isOpen: boolean;
    onToggle: () => void;
}) {
    return (
        <button
            className={`phase w-full cursor-pointer border text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4ade80]/40 ${
                isOpen
                    ? "border-[#4ade80]/60 bg-zinc-800"
                    : "border-transparent hover:bg-zinc-800"
            }`}
            onClick={onToggle}
            aria-expanded={isOpen}
            aria-controls="phase-bouts"
            title="Show the fights in this phase"
        >
            <h4>{title}</h4>
            <div className="phase-row">{phase.fights} fights</div>
            <div className="phase-row">{phase.win_rate}% wins</div>
            <div className="phase-row">Perf {phase.adj_perf}<span className="text-zinc-500"> / 75</span></div>
            <div className="phase-row">Opp {Math.round(phase.opp_strength * 100)}<span className="text-zinc-500"> / 75</span></div>
        </button>
    );
}
