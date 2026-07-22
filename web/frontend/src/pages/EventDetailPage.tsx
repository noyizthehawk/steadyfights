import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getUpcomingEvents, getMyPicks, makePick, AuthError, type UFCEvent } from "../api";

export default function EventDetailPage() {
   //slug from route
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const [event, setEvent] = useState<UFCEvent | null>(null);
    const [error, setError] = useState<string>("");
    // the current user's picks for this event, as { fight_id: picked fighter }
    const [picks, setPicks] = useState<Record<number, string>>({});

    //when slug changes
    useEffect(() => {
        getUpcomingEvents()
            .then((events) => {
                // find the event whose link ends with this slug
                const match = events.find(
                    (e) => e.event_link.split("/").filter(Boolean).pop() === slug
                );
                if (!match) setError("Event not found");
                else setEvent(match);
            })
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load event"));
        // pre-fill any picks this user already made (returns {} when logged out)
        getMyPicks().then(setPicks);
    }, [slug]);

    // Save a pick. Logged-out users get sent to login.
    async function handlePick(fightId: number, fighter: string) {
        try {
            await makePick(fightId, fighter);
            setPicks((prev) => ({ ...prev, [fightId]: fighter }));
        } catch (e) {
            if (e instanceof AuthError) navigate("/login");
            else setError(e instanceof Error ? e.message : "Could not save pick");
        }
    }

    if (error) return <p className="error">{error}</p>;
    if (!event) return <p>Loading…</p>;

    return (
        <div className="event-detail w-full px-6 py-8">
            <Link to="/prediction-game" className="text-sm text-zinc-400">← Back</Link>
            <h1 className="mb-1 text-2xl font-bold text-white">{event.title}</h1>
            <p className="mb-6 text-sm text-zinc-400">
                {new Date(event.date * 1000).toLocaleDateString()} · {event.venue ?? "TBA"}
            </p>

            <ul className="space-y-3">
                {event.fights.map((fight) => {
                    const pickedA = picks[fight.id] === fight.fighter_a;
                    const pickedB = picks[fight.id] === fight.fighter_b;
                    return (
                    // Each fighter is a self-contained column (avatar, name, odds, its own
                    // PICK button) with "vs" between them, so the two sides stay aligned at
                    // any width instead of collapsing into one cramped flex row on a phone.
                    <li
                        key={fight.id}
                        className="grid grid-cols-[1fr_auto_1fr] items-start gap-2 rounded-lg bg-zinc-800 p-3 text-white sm:gap-4 sm:p-4"
                    >
                        {/* fighter a */}
                        <div className="flex min-w-0 flex-col items-center gap-2 sm:flex-row sm:items-center sm:gap-3">
                            {fight.img_a && (
                                // shrink-0 keeps the box square — without it flex squeezes the
                                // width and object-cover crops a full-body sliver.
                                <img src={fight.img_a} alt={fight.fighter_a} className="h-14 w-14 shrink-0 rounded-full object-cover object-top sm:h-16 sm:w-16" />
                            )}
                            <div className="min-w-0 text-center sm:text-left">
                                <p className="truncate text-sm font-semibold sm:text-base">{fight.fighter_a}</p>
                                <p className="text-xs text-zinc-400">{fight.odds_a ?? "—"}</p>
                            </div>
                        </div>

                        <span className="self-center text-zinc-500">vs</span>

                        {/* fighter B */}
                        <div className="flex min-w-0 flex-col items-center gap-2 sm:flex-row-reverse sm:items-center sm:gap-3">
                            {fight.img_b && (
                                <img src={fight.img_b} alt={fight.fighter_b} className="h-14 w-14 shrink-0 rounded-full object-cover object-top sm:h-16 sm:w-16" />
                            )}
                            <div className="min-w-0 text-center sm:text-right">
                                <p className="truncate text-sm font-semibold sm:text-base">{fight.fighter_b}</p>
                                <p className="text-xs text-zinc-400">{fight.odds_b ?? "—"}</p>
                            </div>
                        </div>

                        {/* pick A / pick B sit under their own fighter */}
                        <button
                            onClick={() => handlePick(fight.id, fight.fighter_a)}
                            className={`btn w-full rounded px-3 py-1 text-sm font-display ${pickedA ? "bg-red-600" : "bg-zinc-700 hover:bg-red-600"}`}
                        >
                            {pickedA ? "PICKED" : "PICK"}
                        </button>

                        <span aria-hidden="true" />

                        <button
                            onClick={() => handlePick(fight.id, fight.fighter_b)}
                            className={`btn w-full rounded px-3 py-1 text-sm font-display ${pickedB ? "bg-blue-600" : "bg-zinc-700 hover:bg-blue-600"}`}
                        >
                            {pickedB ? "PICKED" : "PICK"}
                        </button>
                    </li>
                    );
                })}
            </ul>
        </div>
    );
}
