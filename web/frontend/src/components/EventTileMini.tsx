import { Link } from "react-router-dom";
import { UFCEvent } from "../api";
import { eventPhase } from "../lib/lock";


// `highlight` = this is the immediate next event → pulsing red glow.
export function EventTileMini({ event, highlight = false }: { event: UFCEvent; highlight?: boolean }) {
    const slug = event.event_link.split("/").filter(Boolean).pop();
    // A live card outranks "next up": once it has started, the countdown is over,
    // so blue wins even when this is also the soonest event in the list.
    const live = eventPhase(event.date) === "in_progress";
    return (
        <Link to={`/events/${slug}`} className="group block">
            <div
                className={`relative aspect-[3/4] w-full overflow-hidden rounded-xl transition-transform duration-200 group-hover:scale-105 ${
                    live ? "live-glow" : highlight ? "upcoming-glow" : "shadow-lg"
                }`}
            >
                {live && (
                    // Just the dot. The blue glow around the whole tile already
                    // says "live"; a label repeats it and covers the poster.
                    // A ring behind it keeps the dot readable on a bright poster.
                    <span className="absolute left-1.5 top-1.5 z-10 flex h-3 w-3 items-center justify-center rounded-full bg-black/45">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-400 shadow-[0_0_6px_2px_rgba(59,130,246,0.9)]" />
                    </span>
                )}
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
