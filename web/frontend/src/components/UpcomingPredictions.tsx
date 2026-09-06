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
          <div key={e.event_link} className="mb-3">
            {/* Collapsed row: a horizontal slice of the event poster as the
                background. Posters are portrait, so object-cover crops a band
                out of the middle; the gradient keeps the title legible over
                whatever happens to be in that band. */}
            <button
              type="button"
              onClick={() => toggle(e.event_link)}
              aria-expanded={isOpen}
              aria-controls={panelId}
              className="group relative block h-20 w-full cursor-pointer overflow-hidden rounded-xl border border-zinc-700 text-left transition-colors hover:border-[#d33a2c]/60 sm:h-24"
            >
              {e.poster && (
                <img
                  src={e.poster}
                  alt=""
                  aria-hidden
                  loading="lazy"
                  className="absolute inset-0 h-full w-full object-cover object-center opacity-70 transition-transform duration-300 group-hover:scale-105"
                />
              )}
              <div className="absolute inset-0 bg-gradient-to-r from-black via-black/80 to-black/40" />

              <div className="relative flex h-full items-center gap-3 px-4">
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
              <div id={panelId} className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
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
