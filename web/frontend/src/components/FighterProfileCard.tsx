import type { CareerSummary, Phase } from "../api";
import { getCareerSummary } from "../api";
import { useEffect, useState } from "react";
import { NewsList } from "./NewsList";


export function FighterProfileCard({ fighter }: { fighter: string }) {
    const [summary, setSummary] = useState<CareerSummary | null>(null);
    const [error, setError] = useState<string>("");
    const [tab, setTab] = useState<"career" | "news">("career");

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
                        {summary.phases.early && <PhaseColumn title="Early (1–5)" phase={summary.phases.early} />}
                        {summary.phases.mid && <PhaseColumn title="Mid (6–10)" phase={summary.phases.mid} />}
                        {summary.phases.late && <PhaseColumn title="Late (11+)" phase={summary.phases.late} />}
                    </div>
                </>
            )}

            {tab === "news" && <NewsList fighter={summary.fighter} />}
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

function PhaseColumn({ title, phase }: { title: string; phase: Phase }) {
    return (
        <div className="phase">
            <h4>{title}</h4>
            <div className="phase-row">{phase.fights} fights</div>
            <div className="phase-row">{phase.win_rate}% wins</div>
            <div className="phase-row">Adj perf {phase.adj_perf}</div>
            <div className="phase-row">Opp str {phase.opp_strength}</div>
        </div>
    );
}