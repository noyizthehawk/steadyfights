import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
        <div className="prediction-game page">
            <h1>Prediction Game</h1>
            {error && <p className="error">{error}</p>}

            <div className="event-grid">
            {events.map((event) => (
                <EventTile key={event.event_link} event={event} />
            ))}
            </div>
        </div>
        
    );
}
