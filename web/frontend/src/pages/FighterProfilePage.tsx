import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { getCareerSummary, type CareerSummary } from "../api";
import { FighterDetailsCard } from "../components/FighterDetailsCard";
import { FighterProfileCard } from "../components/FighterProfileCard";

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
        <div className="FighterProfilePage page">
            <div className="flex flex-col gap-4">
                <FighterProfileCard summary={summary} />
                <FighterDetailsCard summary={summary} />   
            </div>
        </div>
    );
}
