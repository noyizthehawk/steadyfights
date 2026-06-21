import { useEffect, useState } from "react";
import { getUpcomingEvents } from "../api";
import { EventTile } from "../components/EventTile";
import { UFCEvent } from "../api";
export default function PredictionGamePage() {
    const [events, setEvents] = useState<UFCEvent[]>([]);
    const [error, setError] = useState<string>("");

    useEffect(() => {
        getUpcomingEvents()
        .then(setEvents)
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load events"));    
    }, []);

    return (
        <div className="prediction-game w-full px-6 py-8">
            <h1 className="mb-6 text-2xl font-bold text-white">Prediction Game</h1>
            {error && <p className="error">{error}</p>}

            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {events.map((event) => (
                <EventTile key={event.event_link} event={event} />
            ))}
            </div>
        </div>
        
    );
}
