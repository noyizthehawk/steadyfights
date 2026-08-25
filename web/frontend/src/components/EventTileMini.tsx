import { Link } from "react-router-dom";
import { UFCEvent } from "../api";


export function EventTileMini({ event }: { event: UFCEvent }) {
    const slug = event.event_link.split("/").filter(Boolean).pop();
    return (
        <Link to={`/events/${slug}`} className="group block">
            <div className="aspect-[3/4] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 group-hover:scale-105">
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
            <p
                className="mt-2 break-words text-center text-[9px] leading-tight text-zinc-400"
                style={{ fontFamily: "var(--font-display)" }}
            >
                {event.title}
            </p>
        </Link>
    );
}
