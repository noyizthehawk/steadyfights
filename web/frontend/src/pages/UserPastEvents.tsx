import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { get_user_past_events, type UserEvents } from "../api";
import { PastEventTile } from "../components/PastEventTile";

const GRID =
    "grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6";

export default function UserPastEvents() {
    const { userId } = useParams<{ userId: string }>();
    const [events, setEvents] = useState<UserEvents[]>([]);
    const [error, setError] = useState<string>("");

    useEffect(() => {
        if (!userId) return;
        get_user_past_events(Number(userId))
            .then(setEvents)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
    }, [userId]);

    // Upcoming: soonest first (build-up to the event). Past: most recent first.
    const upcoming = events.filter((e) => e.upcoming).sort((a, b) => a.date - b.date);
    const past = events.filter((e) => !e.upcoming).sort((a, b) => b.date - a.date);

    return (
        <div className="user-events w-full px-6 py-8">
            <h1 className="mb-6 text-2xl font-bold text-white">Events</h1>

            {error && <p className="error">{error}</p>}

            {/* Upcoming predictions — the draw for notable pundits: their picks
                for events that haven't happened yet. */}
            {upcoming.length > 0 && (
                <section className="mb-10">
                    <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-[#d33a2c]">
                        Upcoming Fights
                    </h2>
                    <p className="mb-4 text-sm text-zinc-400">
        
                    </p>
                    <div className={GRID}>
                        {upcoming.map((e) => (
                            <PastEventTile key={e.event_id} userId={Number(userId)} event={e} />
                        ))}
                    </div>
                </section>
            )}

            {/* Past events — their track record. */}
            <section>
                <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-zinc-400">
                    Past events
                </h2>
                <p className="mb-4 text-sm text-zinc-400">
                    
                </p>
                {past.length > 0 ? (
                    <div className={GRID}>
                        {past.map((e) => (
                            <PastEventTile key={e.event_id} userId={Number(userId)} event={e} />
                        ))}
                    </div>
                ) : (
                    <p className="text-zinc-500">No past events yet.</p>
                )}
            </section>

            {events.length === 0 && !error && (
                <p className="text-zinc-500">No events yet.</p>
            )}
        </div>
    );
}
