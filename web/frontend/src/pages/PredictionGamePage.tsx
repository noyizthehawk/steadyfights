import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getUpcomingEvents, me } from "../api";
import { EventTile } from "../components/EventTile";
import { UFCEvent } from "../api";

export default function PredictionGamePage() {
    const [events, setEvents] = useState<UFCEvent[]>([]);
    const [error, setError] = useState<string>("");
    const [userId, setUserId] = useState<number | null>(null); // for the "my past events" link

    useEffect(() => {
        getUpcomingEvents()
        // only events that actually have fights to pick belong in the checker
        .then((evs) => setEvents(evs.filter((e) => e.fights.length > 0)))
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load events"));
        // who's logged in (for the past-events link); null when logged out
        me().then((u) => setUserId(u.id)).catch(() => setUserId(null));
    }, []);

    return (
        <div className="prediction-game w-full px-6 py-8">
            <div className="mb-6 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-white">Available Market</h1>
                {userId !== null && (
                    <Link
                        to={`/users/${userId}/events`}
                        className="text-sm text-zinc-400 hover:text-blue-500"
                    >
                        My Past Events
                    </Link>
                )}
            </div>
            {error && <p className="error">{error}</p>}

            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {events.map((event) => (
                <EventTile key={event.event_link} event={event} />
            ))}
            </div>
        </div>
    );
}
