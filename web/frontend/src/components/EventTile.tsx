import { Link } from "react-router-dom";
import { UFCEvent } from "../api";


export function EventTile({ event }: { event: UFCEvent }) {
    // "/event/ufc-329" -> "ufc-329" : a clean URL-safe id for the detail route
    const slug = event.event_link.split("/").filter(Boolean).pop();
    return (
        <Link
            to={`/events/${slug}`}
            className="group relative block aspect-[3/4] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 hover:scale-105"
        >
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
                <h2 className="text-sm font-semibold text-white">{event.title}</h2>
                <p className="text-xs text-zinc-300 font-bold">
                    {new Date(event.date * 1000).toLocaleDateString()}
                </p>
            </div>
        </Link>
    );
}