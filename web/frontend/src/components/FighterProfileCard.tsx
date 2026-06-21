import type { CareerSummary, Phase } from "../api";
import { getCareerSummary } from "../api";
import { useEffect, useState } from "react";
import { NewsList } from "./NewsList";


export function FighterProfileCard({ fighter }: { fighter: string }) {
    const [summary, setSummary] = useState<CareerSummary | null>(null);
    const [error, setError] = useState<string>("");
    const [tab, setTab] = useState<"career" | "news">("career");
    // which phase's floating panel (PiP) is open, or null when none
    const [activePhase, setActivePhase] = useState<{ title: string; phase: Phase } | null>(null);

    //whenever fighter changes, fetch the summary
    useEffect(() => {
        setSummary(null);
        setError("");
        getCareerSummary(fighter) // 
          .then(setSummary) 
          .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
      }, [fighter]);
    
      if (error) return <div className="card">{error}</div>;
      if (!summary) return <div className="card">Loading…</div>;




    return (
        <div className="border border-zinc-700 rounded-lg p-4">
            <div className="profile-header">
                <h2>{summary.fighter}</h2>
                <span className="career-score" title="Career quality (0–100)">
                    {summary.career_score}
                </span>
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
                        <Stat label="Avg adj. perf" value={summary.avg_adj_perf} hint={summary.perf_label} />
                        <Stat label="Opp strength" value={summary.avg_opp_strength} hint={summary.opp_label} />
                        <Stat label="Volatility" value={summary.volatility} hint={summary.volatility_label} />
                    </div>

                    <div className="career-phases">
                        {summary.phases.early && <PhaseColumn title="Early (1–5)" phase={summary.phases.early} onOpen={setActivePhase} />}
                        {summary.phases.mid && <PhaseColumn title="Mid (6–10)" phase={summary.phases.mid} onOpen={setActivePhase} />}
                        {summary.phases.late && <PhaseColumn title="Late (11+)" phase={summary.phases.late} onOpen={setActivePhase} />}
                    </div>
                </>
            )}

            {tab === "news" && <NewsList fighter={summary.fighter} />}

            {/* pictire in pictire type look */}
            {activePhase && (
                <div className="fixed top-26 right-4 z-50 w-72 rounded-lg border border-zinc-700 bg-zinc-900 p-4 shadow-2xl">
                    <div className="mb-2 flex items-center justify-between">
                        <h4 className="font-semibold text-white">{activePhase.title}</h4>
                        <button
                            className="text-zinc-400 hover:text-white"
                            onClick={() => setActivePhase(null)}
                            aria-label="Close"
                        >
                            ✕
                        </button>
                    </div>
                    <ul className="max-h-[70vh] space-y-1 overflow-y-auto pr-1">
                        {activePhase.phase.bouts.map((b) => (
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
        </div>
    );
}

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
    return (
        <div className="stat">
            <span className="stat-value">{value}</span>
            <span className="stat-label">{label}</span>
            {hint && <span className="stat-hint text-xs text-[#d33a2c]">{hint}</span>}
        </div>
    );
}

function PhaseColumn({
    title,
    phase,
    onOpen,
}: {
    title: string;
    phase: Phase;
    onOpen: (p: { title: string; phase: Phase }) => void;
}) {
    return (
        <button
            className="phase w-full cursor-pointer text-left transition-transform duration-200 hover:scale-105"
            onClick={() => onOpen({ title, phase })}
            title="Click to see the fights in this phase"
        >
            <h4>{title}</h4>
            <div className="phase-row">{phase.fights} fights</div>
            <div className="phase-row">{phase.win_rate}% wins</div>
            <div className="phase-row">Adj perf {phase.adj_perf}</div>
            <div className="phase-row">Opp str {phase.opp_strength}</div>
        </button>
    );
}