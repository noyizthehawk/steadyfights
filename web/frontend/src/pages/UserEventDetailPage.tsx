import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getUserEventCard, type EventCard } from "../api";

// Ring around a fighter's avatar that encodes the pundit's pick + the outcome.
// Position already shows WHICH corner they picked, so color is spent on state:
//   white  = their pick, fight hasn't happened yet
//   green  = the actual winner (also = a correct pick, since they coincide)
//   red    = their pick, but it lost
const RING_OFFSET = "ring-offset-2 ring-offset-zinc-800";
function ringClass(isPicked: boolean, isWinner: boolean, settled: boolean): string {
    if (settled) {
        if (isWinner) return `ring-2 ring-green-500 ${RING_OFFSET}`;
        if (isPicked) return `ring-2 ring-red-500 ${RING_OFFSET}`;
        return "";
    }
    return isPicked ? `ring-2 ring-white/70 ${RING_OFFSET}` : "";
}

export default function UserEventDetailPage() {
    const { userId, eventId } = useParams<{ userId: string; eventId: string }>();
    const navigate = useNavigate();
    const [card, setCard] = useState<EventCard | null>(null);
    const [error, setError] = useState<string>("");

    useEffect(() => {
        if (!userId || !eventId) return;
        getUserEventCard(Number(userId), Number(eventId))
            .then(setCard)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
    }, [userId, eventId]);

    if (error) return <p className="error">{error}</p>;
    if (!card) return <p>Loading…</p>;

    const { user, event, source_video, summary, fights } = card;
    const awaiting = summary.picks_made - summary.fights_settled;

    return (
        <div className="event-detail w-full px-6 py-8">
            <button onClick={() => navigate(-1)} className="text-sm text-zinc-400">
                ← Back
            </button>

            {/* event header */}
            <div className="mt-2 flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white">{event.title}</h1>
                {user.have_youtube && (
                    <span className="rounded bg-[#d33a2c] px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                        YT
                    </span>
                )}
            </div>
            <p className="text-sm text-zinc-400">{user.username}'s predicted card</p>

            {/* source video the picks were extracted from */}
            {source_video && (
                <a
                    href={source_video.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 inline-flex items-center gap-2 rounded-lg bg-zinc-800 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-700"
                >
                    ▶ Watch the breakdown on YouTube
                </a>
            )}

            {/* summary */}
            <div className="mb-6 mt-4 flex flex-wrap items-baseline gap-6">
                <div>
                    <div className="text-3xl font-bold text-white">
                        {summary.winrate === null ? "—" : `${summary.winrate}%`}
                    </div>
                    <div className="text-xs text-zinc-400">win rate</div>
                </div>
                <div className="text-sm text-zinc-400">
                    {summary.correct} of {summary.fights_settled} correct
                    {awaiting > 0 && ` · ${awaiting} awaiting results`}
                </div>
            </div>

            <ul className="space-y-3">
                {fights.map((fight) => {
                    const pickedA = fight.picked === fight.fighter_a;
                    const pickedB = fight.picked === fight.fighter_b;
                    const noPick = fight.picked === null;
                    const ringA = ringClass(pickedA, fight.settled && fight.winner === fight.fighter_a, fight.settled);
                    const ringB = ringClass(pickedB, fight.settled && fight.winner === fight.fighter_b, fight.settled);
                    return (
                        <li
                            key={fight.id}
                            className={`flex items-center justify-between gap-2 rounded-lg p-3 text-white sm:gap-4 sm:p-4 ${
                                noPick ? "bg-zinc-800/40" : "bg-zinc-800"
                            }`}
                        >
                            {/* fighter A */}
                            <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
                                {fight.img_a && (
                                    <img src={fight.img_a} alt={fight.fighter_a} className={`h-11 w-11 shrink-0 rounded-full object-cover object-top sm:h-16 sm:w-16 ${ringA}`} />
                                )}
                                <div className="min-w-0">
                                    <p className={`break-words text-sm font-semibold sm:text-base ${pickedA ? "text-white" : "text-zinc-400"}`}>
                                        {fight.fighter_a}
                                    </p>
                                </div>
                            </div>

                            {/* result badge */}
                            <span className="shrink-0 text-sm font-bold">
                                {noPick ? (
                                    <span className="text-zinc-600">no pick</span>
                                ) : !fight.settled ? (
                                    <span className="text-zinc-500">PENDING</span>
                                ) : fight.correct ? (
                                    <span className="text-green-500">✓</span>
                                ) : (
                                    <span className="text-red-500">✗</span>
                                )}
                            </span>

                            {/* fighter B */}
                            <div className="flex min-w-0 flex-1 items-center justify-end gap-2 text-right sm:gap-3">
                                <div className="min-w-0">
                                    <p className={`break-words text-sm font-semibold sm:text-base ${pickedB ? "text-white" : "text-zinc-400"}`}>
                                        {fight.fighter_b}
                                    </p>
                                </div>
                                {fight.img_b && (
                                    <img src={fight.img_b} alt={fight.fighter_b} className={`h-11 w-11 shrink-0 rounded-full object-cover object-top sm:h-16 sm:w-16 ${ringB}`} />
                                )}
                            </div>
                        </li>
                    );
                })}
            </ul>

            {fights.length === 0 && (
                <p className="text-zinc-500">No fights for this event.</p>
            )}
        </div>
    );
}
