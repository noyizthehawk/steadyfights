/** The caption under an event poster: title in P2, date in the rundown
 *  italic, hung off the red rule — the same caption as the room and fighter
 *  tiles. Divs, not <h2>/<p>: index.css styles those outside any @layer, which
 *  would override the margins and sizes here. */
export function EventCaption({ title, date }: { title: string; date: number }) {
    return (
        <div className="mt-3 border-l-2 border-[#d33a2c] pl-3">
            <div
                className="line-clamp-2 break-words text-[10px] uppercase leading-relaxed text-zinc-200 group-hover:text-white"
                style={{ fontFamily: "var(--font-display)" }}
            >
                {title}
            </div>
            <div
                className="mt-1 text-xs italic text-zinc-500"
                style={{ fontFamily: "var(--font-rundown)" }}
            >
                {new Date(date * 1000).toLocaleDateString(undefined, {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                })}
            </div>
        </div>
    );
}
