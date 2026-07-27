import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getFighters } from "../api";

// Global fighter search for the nav bar. Fetches the full fighter list once and
// filters it client-side (the list is a fixed set, so no backend search needed),
// then navigates to the selected fighter's career page.
export function FighterSearch() {
  const navigate = useNavigate();
  const [all, setAll] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);   // highlighted result (for keyboard nav)
  const boxRef = useRef<HTMLDivElement>(null);

  // Load the fighter list once when the nav mounts.
  useEffect(() => {
    getFighters().then(setAll).catch(() => {});
  }, []);

  // Close the dropdown when clicking outside the search box.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return all.filter((n) => n.toLowerCase().includes(q)).slice(0, 8);
  }, [query, all]);

  function go(name: string) {
    navigate(`/fighters/${encodeURIComponent(name)}/career`);
    setQuery("");
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!matches.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % matches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + matches.length) % matches.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(matches[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={boxRef} className="relative">
      <input
        type="text"
        value={query}
        placeholder="Search fighters…"
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="w-36 rounded-md border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-white placeholder-zinc-500 focus:border-red-500 focus:outline-none sm:w-56"
      />
      {open && matches.length > 0 && (
        <ul className="absolute left-0 z-50 mt-1 max-h-72 w-56 overflow-auto rounded-md border border-zinc-700 bg-zinc-900 shadow-lg">
          {matches.map((name, i) => (
            <li key={name}>
              <button
                // onMouseDown (not onClick) fires before the input's blur, so the
                // dropdown doesn't close out from under the click.
                onMouseDown={(e) => {
                  e.preventDefault();
                  go(name);
                }}
                onMouseEnter={() => setActive(i)}
                className={`block w-full px-3 py-2 text-left text-sm text-white ${
                  i === active ? "bg-zinc-800" : "hover:bg-zinc-800"
                }`}
              >
                {name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
