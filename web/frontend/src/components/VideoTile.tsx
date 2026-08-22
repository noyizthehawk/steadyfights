import { useRef, useState } from "react";
import { Video } from "../api";

// Wide 16:9 carousel of prediction videos: slide through like the news tile
// (arrows + dots), click a thumbnail to play it inline via YouTube's official
// embed player (ToS-compliant — we never re-host, just embed).
export function VideoTile({ videos }: { videos: Video[] }) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [active, setActive] = useState(0);
    const [playing, setPlaying] = useState<string | null>(null);

    if (videos.length === 0) {
        return (
            <div className="flex aspect-video w-full items-center justify-center rounded-xl border border-zinc-800 text-sm text-zinc-500">
                No prediction videos right now.
            </div>
        );
    }

    function onScroll() {
        const el = scrollRef.current;
        if (!el) return;
        setActive(Math.round(el.scrollLeft / el.clientWidth));
    }

    function goTo(i: number) {
        const el = scrollRef.current;
        if (!el) return;
        const clamped = Math.max(0, Math.min(i, videos.length - 1));
        el.scrollTo({ left: clamped * el.clientWidth, behavior: "smooth" });
    }

    return (
        <div className="relative">
            <div
                ref={scrollRef}
                onScroll={onScroll}
                className="flex aspect-video w-full snap-x snap-mandatory overflow-x-auto rounded-xl border border-zinc-800 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
                {videos.map((v) => (
                    <div key={v.video_id} className="relative h-full w-full shrink-0 snap-start">
                        {playing === v.video_id ? (
                            <iframe
                                src={`https://www.youtube.com/embed/${v.video_id}?autoplay=1`}
                                title={v.title}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                                className="h-full w-full"
                            />
                        ) : (
                            <button
                                onClick={() => setPlaying(v.video_id)}
                                className="group relative block h-full w-full"
                                aria-label={`Play: ${v.title}`}
                            >
                                {v.thumbnail ? (
                                    <img src={v.thumbnail} alt={v.title} className="h-full w-full object-cover" />
                                ) : (
                                    <div className="h-full w-full bg-zinc-800" />
                                )}
                                {/* darken + play button */}
                                <div className="absolute inset-0 bg-black/20 transition-colors group-hover:bg-black/40" />
                                <span className="absolute inset-0 flex items-center justify-center">
                                    <span className="flex h-14 w-14 items-center justify-center rounded-full bg-[#d33a2c] text-white shadow-lg transition-transform group-hover:scale-110">
                                        ▶
                                    </span>
                                </span>
                                {/* channel + title */}
                                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-4 text-left">
                                    {v.channel_title && (
                                        <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wide text-[#d33a2c]">
                                            {v.channel_title}
                                        </p>
                                    )}
                                    <p className="line-clamp-2 text-sm font-semibold text-white">{v.title}</p>
                                </div>
                            </button>
                        )}
                    </div>
                ))}
            </div>

            {/* desktop prev/next arrows */}
            {active > 0 && (
                <button
                    onClick={() => goTo(active - 1)}
                    aria-label="Previous"
                    className="absolute left-2 top-1/2 hidden -translate-y-1/2 items-center justify-center rounded-full bg-black/50 p-2 text-white transition-colors hover:bg-black/70 sm:flex"
                >
                    ‹
                </button>
            )}
            {active < videos.length - 1 && (
                <button
                    onClick={() => goTo(active + 1)}
                    aria-label="Next"
                    className="absolute right-2 top-1/2 hidden -translate-y-1/2 items-center justify-center rounded-full bg-black/50 p-2 text-white transition-colors hover:bg-black/70 sm:flex"
                >
                    ›
                </button>
            )}

            {/* dot indicators */}
            <div className="absolute inset-x-0 bottom-3 flex items-center justify-center gap-1.5">
                {videos.map((v, i) => (
                    <button
                        key={v.video_id}
                        onClick={() => goTo(i)}
                        aria-label={`Go to video ${i + 1}`}
                        className={`h-1.5 rounded-full transition-all ${
                            i === active ? "w-4 bg-white" : "w-1.5 bg-white/50 hover:bg-white/80"
                        }`}
                    />
                ))}
            </div>
        </div>
    );
}
