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
                    <li
                        key={fight.id}
                        className="flex items-center justify-between gap-4 rounded-lg bg-zinc-800 p-4 text-white"
                    >
                        {/* fighter a */}
                        <div className="flex flex-1 items-center gap-3">
                            {fight.img_a && (
                                <img src={fight.img_a} alt={fight.fighter_a} className="h-16 w-16 rounded-full object-cover object-top" />
                            )}
                            <div>
                                <p className="font-semibold">{fight.fighter_a}</p>
                                <p className="text-xs text-zinc-400">{fight.odds_a ?? "—"}</p>
                            </div>
                        </div>

                        {/* pick A */}
                        <button
                            onClick={() => handlePick(fight.id, fight.fighter_a)}
                            className={`btn rounded px-3 py-1 text-sm font-display ${pickedA ? "bg-red-600" : "bg-zinc-700 hover:bg-red-600"}`}
                        >
                            {pickedA ? "PICKED" : "PICK"}
                        </button>

                        <span className="text-zinc-500">vs</span>

                        {/* pick B */}
                        <button
                            onClick={() => handlePick(fight.id, fight.fighter_b)}
                            className={`btn rounded px-3 py-1 text-sm font-display ${pickedB ? "bg-blue-600" : "bg-zinc-700 hover:bg-blue-600"}`}
                        >
                            {pickedB ? "PICKED" : "PICK"}
                        </button>

                        {/* fighter B */}
                        <div className="flex flex-1 items-center justify-end gap-3 text-right">
                            <div>
                                <p className="font-semibold">{fight.fighter_b}</p>
                                <p className="text-xs text-zinc-400">{fight.odds_b ?? "—"}</p>
                            </div>
                            {fight.img_b && (
                                <img src={fight.img_b} alt={fight.fighter_b} className="h-16 w-16 rounded-full object-cover object-top" />
                            )}
                        </div>
                    </li>
                    );
                })}
            </ul>
        </div>
    );
}
