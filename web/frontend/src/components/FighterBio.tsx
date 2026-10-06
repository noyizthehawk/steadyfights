import { useEffect, useState } from "react";
import { getFighterBio } from "../api";

/** The written career rundown.
 *
 * Fetched on its own rather than with the career summary: generating one takes
 * around 15 seconds on a cache miss, and the numbers on this page must not wait
 * behind it. Renders nothing at all until it has something to say, so a fighter
 * with no bio leaves no empty box.
 */
export function FighterBio({ fighter }: { fighter: string }) {
    const [body, setBody] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setBody(null);
        getFighterBio(fighter)
            .then((r) => { if (!cancelled) setBody(r.body); })
            // A missing rundown is not worth an error on the page — the rest of
            // the profile is the substance, this is commentary on it.
            .catch(() => { if (!cancelled) setBody(null); })
            .finally(() => { if (!cancelled) setLoading(false); });
        return () => { cancelled = true; };
    }, [fighter]);

    if (loading) {
        return (
            <div className="rounded-lg border border-zinc-700 p-4">
                <div className="mb-3 h-2 w-20 animate-pulse rounded bg-zinc-800" />
                <div className="space-y-2 border-l-2 border-zinc-800 pl-3.5">
                    {[0, 1, 2, 3].map((i) => (
                        <div
                            key={i}
                            className="h-2 animate-pulse rounded bg-zinc-800"
                            style={{ width: `${[100, 96, 88, 60][i]}%` }}
                        />
                    ))}
                </div>
            </div>
        );
    }

    if (!body) return null;

    return (
        <section className="rounded-lg border border-zinc-700 p-4 text-left">
            {/* Same shell, label size and tracking as AgedWell and NextFight
                beside it. The previous version was a solid red slab with 3.5rem
                serif quote marks — a different design language sitting in the
                same column as two hairline-on-black cards. */}
            <h2 className="mb-1 text-[9px] font-medium uppercase tracking-[0.2em] text-zinc-500">
                The rundown
            </h2>
            <p className="mb-3 text-[10px] leading-snug text-zinc-600">
                    Written in collaboration with steadycorp.
            </p>

            {/* A hairline red rule instead of a red fill. It marks the block as
                quoted the way a pull quote does, and spends the accent the way
                the rest of the app spends it — a few pixels, not a panel. */}
            <div className="border-l-2 border-[#d33a2c] pl-3.5">
                <div
                    className="space-y-2.5 text-[12.5px] italic leading-relaxed text-zinc-300"
                    style={{ fontFamily: "var(--font-rundown)" }}
                >
                    {body.split("\n\n").map((para, i) => (
                        <p key={i}>{para.trim()}</p>
                    ))}
                </div>
            </div>
        </section>
    );
}
