import { Link } from "react-router-dom";
import { type UserEvents } from "../api";
import { EventCaption } from "./EventCaption";

// A poster tile for one of a user's past events. Unlike EventTile (which links to
// the generic event page via event_link), this carries userId + event_id so the
// click lands on *that user's* picks for *that event*.
export function PastEventTile({
    userId,
    event,
}: {
    userId: number;
    event: UserEvents;
}) {
    return (
        <Link to={`/users/${userId}/events/${event.event_id}`} className="group block text-left">
            {/* the poster alone — the caption sits underneath */}
            <div className="relative aspect-[3/4] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 group-hover:scale-105">
                {event.poster ? (
                    <img
                        src={event.poster}
                        alt={event.title}
                        className="h-full w-full object-cover"
                    />
                ) : (
                    <div className="flex h-full w-full items-center justify-center bg-zinc-800 text-zinc-400">
                        No image
                    </div>
                )}
            </div>
            <EventCaption title={event.title} date={event.date} />
        </Link>
    );
}
