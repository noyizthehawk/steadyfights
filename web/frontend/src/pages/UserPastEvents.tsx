import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { get_user_past_events, type UserEvents } from "../api";
import { PastEventTile } from "../components/PastEventTile";

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

    return (
        <div className="user-past-events w-full px-6 py-8">
            <h1 className="mb-1 text-2xl font-bold text-white">Past Events</h1>
            <p className="mb-6 text-sm text-zinc-400">
                Events this user made picks in — click one to see how they did.
            </p>

            {error && <p className="error">{error}</p>}

            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                {events.map((e) => (
                    <PastEventTile key={e.event_id} userId={Number(userId)} event={e} />
                ))}
            </div>

            {events.length === 0 && !error && (
                <p className="text-zinc-500">No past events.</p>
            )}
        </div>
    );
}
