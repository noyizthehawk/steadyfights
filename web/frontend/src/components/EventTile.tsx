import { UFCEvent } from "../api";


export function EventTile({ event }: { event: UFCEvent }) {
    return (
        <div className="event-tile">
            <h2>{event.title}</h2>
            <p>{event.date}</p>
            <p>{event.venue}</p>
        </div>       
    );
}