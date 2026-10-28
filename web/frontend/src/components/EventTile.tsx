import { Link } from "react-router-dom";
import { UFCEvent } from "../api";
import { eventPhase } from "../lib/lock";
import { EventCaption } from "./EventCaption";
import { EventPoster } from "./EventPoster";


export function EventTile({ event }: { event: UFCEvent }) {
    // "/event/ufc-329" -> "ufc-329" : a clean URL-safe id for the detail route
    const slug = event.event_link.split("/").filter(Boolean).pop();
    // Derived from the date rather than read off the payload, so it stays right
    // on a re-render without refetching. The API sends `phase` too, for a
    // correct first paint.
    const live = eventPhase(event.date) === "in_progress";
    return (
        <Link to={`/events/${slug}`} className="group block text-left">
            {/* The poster alone — no text on it. The caption sits underneath. */}
            <div
                // Classes are written out in full on both branches: Tailwind scans
                // source text, so a class assembled at runtime is never generated.
                className={
                    live
                        ? "relative aspect-[3/4] w-full overflow-hidden rounded-xl ring-2 ring-blue-500 shadow-[0_0_22px_rgba(59,130,246,0.55)] transition-transform duration-200 group-hover:scale-105"
                        : "relative aspect-[3/4] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 group-hover:scale-105"
                }
            >
                {live && (
                    // Just the dot, as on EventTileMini: the blue ring around the
                    // tile already says "live", and a banner would cover the poster.
                    <span className="absolute left-2 top-2 z-10 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-black/45">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-blue-400 shadow-[0_0_6px_2px_rgba(59,130,246,0.9)]" />
                        <span className="sr-only">In progress</span>
                    </span>
                )}
                <EventPoster src={event.poster} alt={event.title} className="h-full w-full object-cover" />
            </div>
            <EventCaption title={event.title} date={event.date} />
        </Link>
    );
}
