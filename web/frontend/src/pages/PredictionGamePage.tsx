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
        // only events with a venue (real, dated cards) and actual fights to pick
        // belong in the checker  venue-less far-out events are noise.
        .then((evs) => setEvents(evs.filter((e) => e.venue && e.fights.length > 0)))
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load events"));
        // who's logged in (for the past-events link); null when logged out
        me().then((u) => setUserId(u.id)).catch(() => setUserId(null));
    }, []);

    return (
        <div className="prediction-game w-full px-6 py-8">
            <div className="mb-6 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-white">Available Market</h1>
                {userId !== null && (
                    // The app's dot, with its label underneath instead of a red
                    // text link: quiet at rest, fills red with the soft ring on
                    // hover/focus. The padding is the hit area.
                    <Link
                        to={`/users/${userId}/events`}
                        className="group/dot -m-2 flex flex-col items-center gap-1.5 p-2 outline-none"
                    >
                        <span
                            aria-hidden
                            className="block h-2.5 w-2.5 rounded-full bg-white/25 transition-all duration-200 group-hover/dot:scale-110 group-hover/dot:bg-[#d33a2c] group-hover/dot:shadow-[0_0_0_4px_#d33a2c33] group-focus-visible/dot:bg-[#d33a2c] group-focus-visible/dot:shadow-[0_0_0_4px_#d33a2c33]"
                        />
                        <span
                            className="text-[11px] italic leading-none text-zinc-500 transition-colors group-hover/dot:text-zinc-200 group-focus-visible/dot:text-zinc-200"
                            style={{ fontFamily: "var(--font-rundown)" }}
                        >
                            My events
                        </span>
                    </Link>
                )}
            </div>
            {error && <p className="error">{error}</p>}

            <div className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {events.map((event) => (
                <EventTile key={event.event_link} event={event} />
            ))}
            </div>
        </div>
    );
}
