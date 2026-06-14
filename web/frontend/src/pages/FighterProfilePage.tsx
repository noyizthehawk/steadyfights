import { useParams } from "react-router-dom";
import { FighterProfileCard } from "../components/FighterProfileCard";

export default function FighterProfilePage() {
    // The route is /fighters/:id/career, where :id is the fighter's name.
    // React Router URL-decodes it, so "Islam%20Makhachev" -> "Islam Makhachev".
    const { id } = useParams<{ id: string }>();

    if (!id) return <div className="page">No fighter selected.</div>;

    return (
        <div className="FighterProfilePage page">
            <FighterProfileCard fighter={id} />
        </div>
    );
}
