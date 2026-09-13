import { Link } from "react-router-dom";
import { UFCEvent } from "../api";
import { eventPhase } from "../lib/lock";


export function EventTile({ event }: { event: UFCEvent }) {
    // "/event/ufc-329" -> "ufc-329" : a clean URL-safe id for the detail route
    const slug = event.event_link.split("/").filter(Boolean).pop();
    // Derived from the date rather than read off the payload, so it stays right
    // on a re-render without refetching. The API sends `phase` too, for a
    // correct first paint.
    const live = eventPhase(event.date) === "in_progress";
    return (
        <Link
            to={`/events/${slug}`}
                // Classes are written out in full on both branches: Tailwind scans
                // source text, so a class assembled at runtime is never generated.
            className={
                live
                    ? "group relative block aspect-[3/4] w-full overflow-hidden rounded-xl ring-2 ring-blue-500 shadow-[0_0_22px_rgba(59,130,246,0.55)] transition-transform duration-200 hover:scale-105"
                    : "group relative block aspect-[3/4] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 hover:scale-105"
            }
        >
            {live && (
                <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-center gap-1.5 bg-blue-600/90 py-1 text-[9px] font-bold uppercase tracking-[0.18em] text-white">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
                    In progress
                </div>
            )}
            {/* poster fills the tile */}
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

            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-3 text-left">
                <h2 className="break-words text-[11px] font-semibold leading-tight text-white sm:text-xs">
                    {event.title}
                </h2>
                <p className="mt-0.5 text-xs font-bold text-zinc-300">
                    {new Date(event.date * 1000).toLocaleDateString()}
                </p>
            </div>
        </Link>
    );
}