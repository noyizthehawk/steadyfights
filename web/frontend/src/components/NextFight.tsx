import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getUpcomingEvents } from "../api";
import type { Bout, UFCEvent } from "../api";
import { QuickPredictCard } from "./QuickPredictCard";

// ufc.com (the events scrape) and ufcstats (the model) spell names differently —
// accents mostly. Strip diacritics and case before comparing so "Édgar Cháirez"
// on the card matches "Edgar Chairez" on the profile.
const norm = (s: string) =>
  s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

type Found = { event: UFCEvent; fight: Bout };

export function NextFight({ fighter }: { fighter: string }) {
  const [found, setFound] = useState<Found | null>(null);
  const [paywalled, setPaywalled] = useState(false);
  const [freeLeft, setFreeLeft] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    getUpcomingEvents()
      .then((events) => {
        if (cancelled) return;
        // A fighter can legitimately appear more than once across the upcoming
        // slate: scraping.py upserts fights by matchup string and never deletes,
        // so when someone pulls out, the cancelled bout's row survives next to
        // the replacement. Taking the first match would return the OLDEST row —
        // the cancelled one — and invite the user to spend a prediction on a
        // fight that isn't happening.
        //
        // With no status column to ask, the best available signal is the id:
        // it's autoincrement, so the highest one is the most recently scraped,
        // i.e. the replacement. Identical to .find() in the normal single-bout
        // case; only differs when there's a stale row to beat.
        const matches: Found[] = [];
        for (const event of events) {
          for (const fight of event.fights) {
            if (norm(fight.fighter_a) === norm(fighter) || norm(fight.fighter_b) === norm(fighter)) {
              matches.push({ event, fight });
            }
          }
        }
        if (!matches.length) return setFound(null);
        setFound(matches.reduce((a, b) => (b.fight.id > a.fight.id ? b : a)));
      })
      .catch(() => setFound(null));   // no upcoming bout is the normal case, not an error
    return () => {
      cancelled = true;
    };
  }, [fighter]);

  // Most fighters aren't booked at any given moment — render nothing rather than
  // an empty "no scheduled bout" box on the majority of profiles.
  if (!found) return null;

  const { event, fight } = found;

  return (
    <section className="rounded-lg border border-zinc-700 p-4 text-left">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-[9px] font-medium uppercase tracking-[0.2em] text-zinc-500">
          Next fight
        </h2>
        <span className="shrink-0 text-[10px] tabular-nums text-zinc-500">
          {new Date(event.date * 1000).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </span>
      </div>

      <div className="mb-3 truncate font-display text-[10px] uppercase text-zinc-300 max-sm:text-[9px]">
        {event.title}
      </div>

      {/* The matchup is free information; the model's call is not. Same card and
          same allowance as Quick Predict, so a tap here costs exactly what a tap
          on the Bout Brain page costs. */}
      <QuickPredictCard
        fight={fight}
        paywalled={paywalled}
        onFreeLeft={setFreeLeft}
        onPaywall={() => setPaywalled(true)}
      />

      {/* Predicting and picking are different acts: one asks the model, the
          other commits the user to a call that gets scored. The predict button
          lives inside QuickPredictCard above, so this sits directly under it. */}
      {/* Solid red, no border. This is the one thing on the card we want the
          user to actually do, and an outlined tinted button reads as secondary —
          the same weight as a "learn more". The sheen sweeps once on hover
          rather than looping: a permanently animated control is noise, but a
          surface that responds to the cursor says "this is live". */}
      <Link
        to={`/events/${event.event_link.split("/").filter(Boolean).pop()}`}
        className="group relative mt-3 flex w-full items-center justify-center gap-2 overflow-hidden rounded-lg bg-[#d33a2c] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wide text-white transition-all duration-200 hover:bg-[#e8503f] hover:shadow-[0_4px_16px_-2px_rgba(211,58,44,0.5)] active:scale-[0.98]"
      >
        <span className="relative z-10">Make your picks</span>
        <svg
          viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
          strokeLinecap="round" strokeLinejoin="round"
          className="relative z-10 h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5"
        >
        </svg>
        {/* -translate-x-full -> translate-x-full, so the highlight crosses the
            button once per hover and parks off the far edge. */}
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 ease-out group-hover:translate-x-full"
        />
      </Link>

      {paywalled ? (
        <p className="mt-3 text-[11px] leading-snug text-zinc-400">
          You've used your free predictions.{" "}
          <Link to="/predictor" className="text-[#d33a2c] underline underline-offset-2">
            Subscribe to keep going
          </Link>
        </p>
      ) : (
        freeLeft !== null && (
          <p className="mt-3 text-[10px] tabular-nums text-zinc-500">
            {freeLeft} free prediction{freeLeft === 1 ? "" : "s"} left
          </p>
        )
      )}
    </section>
  );
}
