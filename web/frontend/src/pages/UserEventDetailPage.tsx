import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getUserEventStats, type UserEventStats } from "../api";

export default function UserEventDetailPage() {
    const { userId, eventId } = useParams<{ userId: string; eventId: string }>();
    const navigate = useNavigate();
    const [stats, setStats] = useState<UserEventStats | null>(null);
    const [error, setError] = useState<string>("");

    useEffect(() => {
        if (!userId || !eventId) return;
        getUserEventStats(Number(userId), Number(eventId))
            .then(setStats)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
    }, [userId, eventId]);

    if (error) return <p className="error">{error}</p>;
    if (!stats) return <p>Loading…</p>;

    return (
        <div className="event-detail w-full px-6 py-8">
            <button onClick={() => navigate(-1)} className="text-sm text-zinc-400">
                ← Back
            </button>

            {/* summary card */}
            <div className="mb-6 mt-2 flex flex-wrap items-baseline gap-6">
                <div>
                    <div className="text-3xl font-bold text-white">
                        {stats.winrate === null ? "—" : `${stats.winrate}%`}
                    </div>
                    <div className="text-xs text-zinc-400">win rate</div>
                </div>
                <div className="text-sm text-zinc-400">
                    {stats.correct}/{stats.fights_settled} correct
                    {" · "}
                    {stats.picks_made} picks made
                </div>
            </div>

            <ul className="space-y-3">
                {stats.fights.map((fight) => {
                    const pickedA = fight.picked === fight.fighter_a;
                    const pickedB = fight.picked === fight.fighter_b;
                    const settled = fight.winner !== null;
                    return (
                        <li
                            key={fight.matchup}
                            className="flex items-center justify-between gap-4 rounded-lg bg-zinc-800 p-4 text-white"
                        >
                            {/* fighter A */}
                            <div className="flex flex-1 items-center gap-3">
                                {fight.img_a && (
                                    <img src={fight.img_a} alt={fight.fighter_a} className="h-16 w-16 rounded-full object-cover object-top" />
                                )}
                                <div>
                                    <p className={`font-semibold ${pickedA ? "text-white" : "text-zinc-400"}`}>
                                        {fight.fighter_a}
                                        {pickedA && <span className="ml-2 text-xs text-zinc-500">(picked)</span>}
                                    </p>
                                    {settled && fight.winner === fight.fighter_a && (
                                        <p className="text-xs font-bold text-green-500">WINNER</p>
                                    )}
                                </div>
                            </div>

                            {/* result badge */}
                            <span className="text-sm font-bold">
                                {!settled ? (
                                    <span className="text-zinc-500">PENDING</span>
                                ) : fight.correct ? (
                                    <span className="text-green-500">✓</span>
                                ) : (
                                    <span className="text-red-500">✗</span>
                                )}
                            </span>

                            {/* fighter B */}
                            <div className="flex flex-1 items-center justify-end gap-3 text-right">
                                <div>
                                    <p className={`font-semibold ${pickedB ? "text-white" : "text-zinc-400"}`}>
                                        {fight.fighter_b}
                                        {pickedB && <span className="ml-2 text-xs text-zinc-500">(picked)</span>}
                                    </p>
                                    {settled && fight.winner === fight.fighter_b && (
                                        <p className="text-xs font-bold text-green-500">WINNER</p>
                                    )}
                                </div>
                                {fight.img_b && (
                                    <img src={fight.img_b} alt={fight.fighter_b} className="h-16 w-16 rounded-full object-cover object-top" />
                                )}
                            </div>
                        </li>
                    );
                })}
            </ul>

            {stats.fights.length === 0 && (
                <p className="text-zinc-500">No picks for this event.</p>
            )}
        </div>
    );
}
