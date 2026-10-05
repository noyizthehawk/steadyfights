import type { CareerSummary, Phase } from "../api";
import { useState } from "react";
import { NewsList } from "./NewsList";
import { Ring, Bar, Figure, CareerScore, RING_RANGE } from "./Meters";

// Card 2: career statistics (performance IQ, form, phases, news). Receives the
// already-fetched summary from the page so both cards share one request.
export function FighterProfileCard({ summary }: { summary: CareerSummary }) {
    const [tab, setTab] = useState<"career" | "news">("career");
    // Titles currently expanded. A set rather than a single title: the panels
    // stack full-width below the row, so any number can be open at once.
    const [openPhases, setOpenPhases] = useState<Set<string>>(new Set());

    // filter out phases the fighter never reached (a 4-fight career has no mid)
    const phaseList = ([
        ["Early", "early", "1–5", summary.phases.early],
        ["Mid", "mid", "6–10", summary.phases.mid],
        ["Late", "late", "11+", summary.phases.late],
    ] as [string, "early" | "mid" | "late", string, Phase | undefined][])
        .filter((e): e is [string, "early" | "mid" | "late", string, Phase] => Boolean(e[3]));
    const allOpen = phaseList.length > 0 && phaseList.every(([t]) => openPhases.has(t));
    const toggle = (title: string) =>
        setOpenPhases((prev) => {
            const next = new Set(prev);
            if (!next.delete(title)) next.add(title);
            return next;
        });

    return (
        <div className="relative rounded-lg border border-zinc-700 p-4 text-left">
            <div className="profile-header">
                <div className="flex min-w-0 flex-wrap items-baseline gap-x-2.5 gap-y-1">
                    <h2 className="text-xl font-bold text-white sm:text-2xl">{summary.fighter}</h2>
                    <span className="whitespace-nowrap text-xl font-bold tabular-nums text-red-500 sm:text-2xl">{summary.record}</span>
                    <ActivityChip activity={summary.activity} />
                </div>
                <div className="flex shrink-0 items-center gap-2">
                    <CareerScore value={summary.career_score} />
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

                    {/* Rings for the four 0-100 scores — each is one ratio
                        against a fixed limit, which is a meter. Counts and
                        rates are plain figures: a ring implies a ceiling, and a
                        fight count has none.

                        One grid, no wrapping panel. Each metric carries its own
                        cell border, so an outer box around them only drew a
                        second line a few pixels from the first. */}
                    <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                        <Ring value={summary.avg_adj_perf} label="Overall Performance" hint={summary.perf_label} />
                        <Ring value={summary.recent_perf} label="Recent Performance" hint={`${summary.recent_record} last 5`} delta={summary.recent_perf - summary.avg_adj_perf} />
                        <Ring value={summary.avg_opp_strength} label="Overall Opponent Strength" hint={summary.opp_label} />
                        <Ring value={summary.recent_opp_strength} label="Recent Opponent Strength" hint={summary.recent_opp_label} delta={summary.recent_opp_strength - summary.avg_opp_strength} />
                    </div>

                    <div className="mt-2 grid grid-cols-3 gap-2">
                        <Figure value={summary.total_fights} label="Fights" />
                        <Figure value={`${summary.win_rate}%`} label="Win rate" />
                        <Figure value={summary.volatility} label="Volatility" hint={summary.volatility_label} />
                    </div>

                    <div className="mt-4 mb-2 flex items-baseline justify-between gap-3">
                        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                            Career phases
                        </h3>
                        <button
                            onClick={() => setOpenPhases(allOpen ? new Set() : new Set(phaseList.map(([t]) => t)))}
                            className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[#d33a2c] transition-colors hover:text-[#e8503f]"
                        >
                            {allOpen ? "Collapse all" : "Expand all"}
                        </button>
                    </div>

                    <div className="career-phases">
                        {phaseList.map(([title, kind, range, phase]) => (
                            <PhaseColumn
                                key={title}
                                title={title}
                                kind={kind}
                                range={range}
                                phase={phase}
                                isOpen={openPhases.has(title)}
                                onToggle={() => toggle(title)}
                            />
                        ))}
                    </div>

                    {/* One panel per open phase, stacked below the row. A card
                        is one grid column wide on desktop — far too narrow for
                        a list of opponent names — so the fights live out here
                        and the card's button just toggles them. Each panel
                        borrows its phase's accent so it reads as belonging to
                        the card above it. */}
                    {phaseList.filter(([t]) => openPhases.has(t)).map(([title, kind, range, phase]) => (
                        <div
                            key={title}
                            className="mt-3 rounded-lg border bg-[#0d0d0d] p-3"
                            style={{ borderColor: `${PHASE_ACCENT[kind]}66` }}
                        >
                            <div className="mb-2 flex items-baseline justify-between gap-3">
                                <h4
                                    className="text-[11px] font-semibold uppercase tracking-wide"
                                    style={{ color: PHASE_ACCENT[kind] }}
                                >
                                    {title} ({range})
                                </h4>
                                <span className="shrink-0 text-[10px] tabular-nums text-zinc-500">
                                    {phase.bouts.length} fight{phase.bouts.length === 1 ? "" : "s"}
                                </span>
                            </div>
                            <ul className="max-h-72 space-y-1 overflow-y-auto pr-1">
                                {phase.bouts.map((b) => (
                                    <li key={b.fight_number} className="flex items-center gap-2 text-xs">
                                        {/* Career fight number, not a row index — it
                                            is the same number the phase ranges are
                                            cut on ("Late (11+)"), so the list ties
                                            back to the tile it came from. */}
                                        <span className="w-4 shrink-0 text-right text-[10px] tabular-nums text-zinc-600">
                                            {b.fight_number}
                                        </span>
                                        <span className={`flex h-4 w-5 shrink-0 items-center justify-center rounded text-[9px] font-bold leading-none text-white ${b.won ? "bg-green-500" : "bg-red-500"}`}>
                                            {b.won ? "W" : "L"}
                                        </span>
                                        <a
                                            href={`/fighters/${encodeURIComponent(b.opponent)}/career`}
                                            className="min-w-0 flex-1 truncate text-white hover:text-zinc-400 hover:underline"
                                        >
                                            {b.opponent}
                                        </a>
                                        {/* Method and year, right-aligned in their own
                                            columns so they line up down the list instead
                                            of ragging after names of different lengths. */}
                                        {b.method && (
                                            <span className="shrink-0 text-[10px] font-semibold tabular-nums text-zinc-400">
                                                {b.method}
                                            </span>
                                        )}
                                        {b.date && (
                                            <span className="w-8 shrink-0 text-right text-[10px] tabular-nums text-zinc-600">
                                                {b.date.slice(0, 4)}
                                            </span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
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

// Per-phase identity colour. Categorical, not a value ramp: the gradient says
// WHICH phase you're looking at, and must not move when the numbers do. The
// bars inside carry value separately.
// Per-phase identity colour. Categorical, not a value ramp: it says WHICH phase
// you are looking at and must not move when the numbers do. The bars inside
// carry value separately.
//
// The gradient is derived from the accent rather than written out separately,
// so the two can never drift apart — the card wash and its subtitle, dot and
// open border are all one colour.
const PHASE_ACCENT = {
    early: "#22e07a",
    mid: "#818cf8",
    late: "#ff9a4d",
} as const;

/** A barely-there wash over near-black.
 *
 * The mockup's gradients were full-saturation panels, which read as three
 * coloured blocks competing with the data on top of them. At 10% and 4% the
 * hue is just enough to tell the phases apart at a glance while the card still
 * belongs to a black page — colour peeking through rather than painted on.
 */
function phaseWash(accent: string): string {
    return `radial-gradient(120% 120% at 100% 0%, ${accent}1a 0%, ${accent}0a 45%, transparent 100%), #0a0a0b`;
}

function PhaseColumn({
    title,
    kind,
    range,
    phase,
    isOpen,
    onToggle,
}: {
    title: string;
    kind: "early" | "mid" | "late";
    range: string;
    phase: Phase;
    isOpen: boolean;
    onToggle: () => void;
}) {
    const accent = PHASE_ACCENT[kind];
    return (
        <div>
            <button
                type="button"
                onClick={onToggle}
                aria-expanded={isOpen}
                className="relative flex min-h-[15.5rem] w-full cursor-pointer flex-col overflow-hidden rounded-[14px] border p-5 text-left transition-transform duration-200 hover:-translate-y-[3px] hover:shadow-[0_12px_30px_rgba(0,0,0,.5)] focus-visible:outline-none focus-visible:ring-2"
                style={{
                    background: phaseWash(accent),
                    borderColor: isOpen ? `${accent}66` : "rgba(255,255,255,.08)",
                }}
            >
                {/* Oversized range number, bottom-right, barely visible. Press
                    Start 2P advances a full em per glyph, so this is sized well
                    below the mockup's 170px or "11+" alone would be ~360px. */}
                <span
                    aria-hidden
                    className="pointer-events-none absolute -bottom-3 right-0 select-none leading-none text-white/[0.06]"
                    style={{ fontFamily: "var(--font-display)", fontSize: "2.75rem" }}
                >
                    {range}
                </span>
                <div className="relative flex items-start justify-between gap-3">
                    <div className="min-w-0">
                        <h2
                            className="uppercase leading-none text-white"
                            style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem" }}
                        >
                            {title}
                        </h2>
                        <span className="mt-1.5 block text-[10px] font-extrabold italic tracking-[0.06em]" style={{ color: accent }}>
                            FIGHTS {range}
                        </span>
                    </div>
                    <div className="shrink-0 text-right">
                        <b className="block leading-none text-white" style={{ fontFamily: "var(--font-display)", fontSize: "1rem" }}>
                            {phase.win_rate}%
                        </b>
                        <small className="block text-[9px] font-bold tracking-[0.1em] text-white/70">WIN RATE</small>
                        {/* Same treatment as "FIGHTS 1–5" opposite, so the two
                            sides of the header balance: accent, italic, same
                            size. The range and the count are the same kind of
                            fact and should look it. */}
                        <small
                            className="mt-1.5 block text-[10px] font-extrabold italic tabular-nums tracking-[0.06em]"
                            style={{ color: accent }}
                        >
                            {phase.fights} FIGHT{phase.fights === 1 ? "" : "S"}
                        </small>
                    </div>
                </div>

                <div className="relative mt-auto grid gap-3 pt-[18px]">
                    <Bar value={phase.adj_perf} label="Performance" max={75} />
                    <Bar value={Math.round(phase.opp_strength * 100)} label="Opposition" max={75} />
                </div>

                {/* A dot. It fills with the phase accent when open, so state
                    reads without any words — and because the whole card is the
                    button, this only has to mark that something is there. */}
                <span
                    aria-hidden
                    className="relative mt-4 h-1.5 w-1.5 self-start rounded-full transition-all duration-200"
                    style={{
                        background: isOpen ? accent : "rgba(255,255,255,.25)",
                        boxShadow: isOpen ? `0 0 0 4px ${accent}22` : "none",
                    }}
                />

            </button>
        </div>
    );
}
