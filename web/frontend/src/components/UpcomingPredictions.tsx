import { useEffect, useState } from "react";
import { getUpcomingEvents } from "../api";
import type { UFCEvent } from "../api";
import { QuickPredictCard } from "./QuickPredictCard";

type Props = {
  /** every fighter name the model knows, from /api/fighters */
  known: string[];
  paywalled: boolean;
  onFreeLeft: (n: number | null) => void;
  onPaywall: () => void;
};

export function UpcomingPredictions({ known, paywalled, onFreeLeft, onPaywall }: Props) {
  const [events, setEvents] = useState<UFCEvent[]>([]);
  const [error, setError] = useState("");
  // event_links that are expanded. A Set rather than a single value so opening
  // one card doesn't collapse another the user is still reading.
  const [open, setOpen] = useState<Set<string>>(new Set());

  useEffect(() => {
    getUpcomingEvents()
      .then(setEvents)
      .catch(() => setError("Couldn't load upcoming fights."));
  }, []);

  // built once per render rather than per card — 42 fights x 2747 names otherwise
  const knownSet = new Set(known);

  function toggle(link: string) {
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(link) ? next.delete(link) : next.add(link);
      return next;
    });
  }

  if (error) return <p className="error">{error}</p>;
  if (!events.length) return null;

  return (
    <section className="w-full text-left">

      {events.map((e) => {
        const isOpen = open.has(e.event_link);
        const panelId = `qp-${e.event_link.replace(/[^a-z0-9]+/gi, "-")}`;
        return (
          <div key={e.event_link} className="mb-2.5 sm:mb-3">
            {/* Collapsed row: a horizontal slice of the event poster as the
                background. Posters are portrait, so object-cover crops a band
                out of the middle; the gradient keeps the title legible over
                whatever happens to be in that band. */}
            <button
              type="button"
              onClick={() => toggle(e.event_link)}
              aria-expanded={isOpen}
              aria-controls={panelId}
              className={`group relative block h-[68px] w-full cursor-pointer overflow-hidden rounded-xl border text-left transition-[border-color,transform] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4ade80]/40 active:scale-[0.995] sm:h-24 ${
                isOpen ? "border-[#4ade80]/60" : "border-zinc-800 hover:border-[#4ade80]/35"
              }`}
            >
              {e.poster && (
                <img
                  src={e.poster}
                  alt=""
                  aria-hidden
                  loading="lazy"
                  className="absolute inset-0 h-full w-full object-cover object-center opacity-60 transition-transform duration-300 group-hover:scale-105 group-active:scale-105"
                />
              )}
              <div className="absolute inset-0 bg-gradient-to-r from-black via-black/85 to-black/45" />

              {/* Character-select reticle: four corner Ls rather than a closed
                  border, so it reads as "this one is selected" the way a
                  fighting game's select grid marks the highlighted portrait.
                  Each span sets only its two adjacent borders. */}
              {[
                "left-1.5 top-1.5 border-l-2 border-t-2",
                "right-1.5 top-1.5 border-r-2 border-t-2",
                "left-1.5 bottom-1.5 border-l-2 border-b-2",
                "right-1.5 bottom-1.5 border-r-2 border-b-2",
              ].map((pos) => (
                <span
                  key={pos}
                  aria-hidden
                  className={`pointer-events-none absolute h-3 w-3 border-[#4ade80] transition-all duration-150 ${pos} ${
                    isOpen ? "scale-100 opacity-100" : "scale-50 opacity-0"
                  }`}
                />
              ))}

              <div className="relative flex h-full items-center gap-3 px-3.5 sm:px-4">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-display text-[11px] uppercase text-white max-sm:text-[9px]">
                    {e.title}
                  </div>
                  <div className="mt-1.5 text-[10px] tabular-nums text-zinc-400">
                    {new Date(e.date * 1000).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                    {" · "}
                    {e.fights.length} fight{e.fights.length === 1 ? "" : "s"}
                  </div>
                </div>
              </div>
            </button>

            {isOpen && (
              <div id={panelId} className="mt-2.5 grid grid-cols-1 gap-2.5 sm:mt-3 sm:grid-cols-2 sm:gap-3">
                {e.fights.map((f) => (
                  <QuickPredictCard
                    key={f.id}
                    fight={f}
                    known={knownSet}
                    paywalled={paywalled}
                    onFreeLeft={onFreeLeft}
                    onPaywall={onPaywall}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
}
