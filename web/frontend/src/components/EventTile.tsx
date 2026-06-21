import { UFCEvent } from "../api";


export function EventTile({ event }: { event: UFCEvent }) {
    return (
        <button className="group relative aspect-[3/4] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 hover:scale-105">
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

            {/* dark gradient so text is readable over any poster */}
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-3 text-left">
                <h2 className="text-sm font-semibold text-white">{event.title}</h2>
                <p className="text-xs text-zinc-300">
                    {new Date(event.date * 1000).toLocaleDateString()}
                </p>
            </div>
        </button>
    );
}