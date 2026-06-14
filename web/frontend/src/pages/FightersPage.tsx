import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getFighters } from "../api";

export default function FightersPage() {
  const [fighters, setFighters] = useState<string[]>([]);
  const [error, setError] = useState<string>("");
  const [query, setQuery] = useState<string>("");

  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load fighters"));
  }, []);

  // Case-insensitive name filter Empty query shows everyone.
  const q = query.trim().toLowerCase();
  const visible = q ? fighters.filter((name) => name.toLowerCase().includes(q)) : [];

  return (
    
    <div className="FightersPage page">
      <h1>Fighters</h1>
      {error && <p className="error">{error}</p>}

      <input
        className="fighter-search"
        type="text"
        value={query}
        placeholder="Search fighters…"
        onChange={(e) => setQuery(e.target.value)}
      />

      {q && (
        <ul className="fighter-list">
          {visible.map((name) => (
            <li key={name}>
              <Link to={`/fighters/${encodeURIComponent(name)}/career`}>{name}</Link>
            </li>
          ))}
          {visible.length === 0 && (
            <li className="fighter-count">No fighters match “{query}”.</li>
          )}
        </ul>
      )}
    </div>
  );
}
