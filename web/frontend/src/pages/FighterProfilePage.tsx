import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getCareerSummary, type CareerSummary } from "../api";
import { FighterDetailsCard } from "../components/FighterDetailsCard";
import { FighterProfileCard } from "../components/FighterProfileCard";
import { NextFight } from "../components/NextFight";
import { CareerChart } from "../components/CareerChart";
import { AgedWell } from "../components/AgedWell";

export default function FighterProfilePage() {
    // The route is /fighters/:id/career, where :id is the fighter's name.
    // React Router URL-decodes it, so "Islam%20Makhachev" -> "Islam Makhachev".
    const { id } = useParams<{ id: string }>();
    const [summary, setSummary] = useState<CareerSummary | null>(null);
    const [error, setError] = useState<string>("");

    // Fetch once here; both cards share the result.
    useEffect(() => {
        if (!id) return;
        setSummary(null);
        setError("");
        getCareerSummary(id)
            .then(setSummary)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed"));
    }, [id]);

    if (!id) return <div className="page">No fighter selected.</div>;
    if (error) return <div className="page">{error}</div>;
    if (!summary) return <div className="page">Loading…</div>;

    return (
        // not .page — that caps at 640px, too narrow for two columns. Same shape
        // as the landing and Bout Brain pages: one wide container, stacked below
        // lg, side by side above.
        <div className="FighterProfilePage mx-auto w-full max-w-6xl px-3 py-8 text-left sm:px-4">
            <section className="flex flex-col gap-5 sm:gap-6 lg:flex-row lg:items-start">
                <div className="flex min-w-0 flex-1 flex-col gap-5 sm:gap-6">
                    <FighterProfileCard summary={summary} />
                    {/* renders nothing under 3 fights — two points aren't a trend */}
                    <CareerChart timeline={summary.timeline} />
                    <FighterDetailsCard summary={summary} />
                </div>

                {/* NextFight renders nothing when the fighter isn't booked, which
                    is most of them — the aside then collapses to zero width and
                    the cards take the full row. */}
                {/* right rail: both render nothing when they have nothing to say,
                    so an unbooked fighter with no notable opponents collapses it */}
                <aside className="flex flex-col gap-5 sm:gap-6 lg:w-80 lg:shrink-0">
                    <NextFight fighter={summary.fighter} />
                    <AgedWell rows={summary.aged_well} fighter={summary.fighter} />
                </aside>
            </section>
        </div>
    );
}
