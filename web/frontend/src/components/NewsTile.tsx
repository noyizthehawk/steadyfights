import { useRef, useState } from "react";
import { NewsArticle } from "../api";


export function NewsTile({ articles }: { articles: NewsArticle[] }) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [active, setActive] = useState(0);

    if (articles.length === 0) {
        return (
            <div className="flex h-[520px] items-center justify-center rounded-xl border border-zinc-800 text-sm text-zinc-500">
                No news right now.
            </div>
        );
    }

    // keep `active` in sync as the user scrolls/swipes
    function onScroll() {
        const el = scrollRef.current;
        if (!el) return;
        setActive(Math.round(el.scrollLeft / el.clientWidth));
    }

    function goTo(i: number) {
        const el = scrollRef.current;
        if (!el) return;
        const clamped = Math.max(0, Math.min(i, articles.length - 1));
        el.scrollTo({ left: clamped * el.clientWidth, behavior: "smooth" });
    }

    return (
        <div className="relative">
            {/* slides */}
            <div
                ref={scrollRef}
                onScroll={onScroll}
                className="flex h-[520px] snap-x snap-mandatory overflow-x-auto rounded-xl border border-zinc-800 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
                {articles.map((a) => (
                    <a
                        key={a.url}
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="relative flex h-full w-full shrink-0 snap-start items-end overflow-hidden"
                    >
                        {a.image ? (
                            <img src={a.image} alt={a.title} className="absolute inset-0 h-full w-full object-cover" />
                        ) : (
                            <div className="absolute inset-0 bg-zinc-800" />
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent" />
                        <div className="relative p-4 pb-8">
                            {a.source && (
                                <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[#d33a2c]">
                                    {a.source}
                                </p>
                            )}
                            <p className="text-sm font-semibold leading-snug text-white line-clamp-3">
                                {a.title}
                            </p>
                        </div>
                    </a>
                ))}
            </div>

            {/* desktop prev/next arrows (hidden on touch-first small screens) */}
            {active > 0 && (
                <button
                    onClick={() => goTo(active - 1)}
                    aria-label="Previous"
                    className="absolute left-2 top-1/2 hidden -translate-y-1/2 items-center justify-center rounded-full bg-black/50 p-2 text-white transition-colors hover:bg-black/70 sm:flex"
                >
                    ‹
                </button>
            )}
            {active < articles.length - 1 && (
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
                {articles.map((a, i) => (
                    <button
                        key={a.url}
                        onClick={() => goTo(i)}
                        aria-label={`Go to news ${i + 1}`}
                        className={`h-1.5 rounded-full transition-all ${
                            i === active ? "w-4 bg-white" : "w-1.5 bg-white/50 hover:bg-white/80"
                        }`}
                    />
                ))}
            </div>
        </div>
    );
}
