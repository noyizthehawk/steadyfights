import { Children, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getBrowseFighters, getFighters, type BrowseFighters } from "../api";
import { FighterCard } from "../components/FighterCard";

/** Shared by the real cards and the loading skeletons so both lay out the same. */
const GRID = "grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6";

/** Section heading: P2, hung off the red rule. An <h3> on purpose — index.css
 *  styles h1/h2 outside any @layer, which would override these classes.
 *  `action` sits at the far right, the usual home of a "Show all". */
function SectionHeading({
  title,
  meta,
  action,
}: {
  title: string;
  meta?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 border-l-2 border-[#d33a2c] pl-3">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h3
          className="m-0 text-[11px] uppercase leading-relaxed text-white"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {title}
        </h3>
        {meta && (
          <div className="text-xs italic text-zinc-500" style={{ fontFamily: "var(--font-rundown)" }}>
            {meta}
          </div>
        )}
      </div>
      {action}
    </div>
  );
}

/** "Show all N" / "Show less" for an ExpandableRow, in the app's dot language
 *  (the career-phase cards, the room cover picker): a quiet dot at rest that
 *  fills with the section's accent and picks up a soft ring when open, so the
 *  state reads without words. */
function ShowAllToggle({
  expanded,
  total,
  onToggle,
  accent,
}: {
  expanded: boolean;
  total: number;
  onToggle: (e: React.MouseEvent<HTMLButtonElement>) => void;
  accent: string;
}) {
  const label = expanded ? "Show less" : `Show all ${total}`;
  return (
    // The padding is the hit area — the dot alone is too small a target.
    // Named by title (hover) + sr-only text (screen readers), no visible words.
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={expanded}
      title={label}
      className="group/dot -m-2 flex cursor-pointer items-center gap-1.5 p-2"
    >
      {/* the count, collapsed only: without it, phone users (no hover, so no
          tooltip) can't tell the section opens or how much is behind it */}
      {!expanded && (
        <span aria-hidden className="text-[10px] tabular-nums text-zinc-500 group-hover/dot:text-zinc-300">
          {total}
        </span>
      )}
      <span
        aria-hidden
        className="block h-2.5 w-2.5 rounded-full transition-all duration-200 group-hover/dot:scale-110"
        style={{
          background: expanded ? accent : "rgba(255,255,255,.25)",
          boxShadow: expanded ? `0 0 0 4px ${accent}33` : "none",
        }}
      />
      <span className="sr-only">{label}</span>
    </button>
  );
}

/** The second "Show less" dot, bottom-right of an OPEN section. Opened, a list
 *  runs several rows deep and the top dot has scrolled away; this one closes
 *  it from where the reader finished. Closing shrinks the section under them,
 *  so it then brings the section's top back into view — otherwise they'd be
 *  left staring at whatever came after it. */
function CloseDot({ onClose, accent }: { onClose: () => void; accent: string }) {
  // a second tap mid-glide would toggle the section back OPEN
  const closing = useRef(false);
  return (
    <div className="mt-4 flex justify-end">
      <ShowAllToggle
        expanded
        total={0}
        accent={accent}
        onToggle={async (e) => {
          if (closing.current) return;
          closing.current = true;
          const section = e.currentTarget.closest("section");
          // Glide up FIRST, then fold. Doing both at once (the old way) let
          // the page shrink under a moving scroll, which read as a snap. Only
          // glides when the top is off screen — a short, fully visible
          // section just folds.
          if (section) {
            const top = section.getBoundingClientRect().top - 24;   // scroll-mt-6
            if (top < 0) await glideBy(top);
          }
          onClose();
          closing.current = false;
        }}
      />
    </div>
  );
}

/** Scroll the window by `dy` px with an ease-in-out curve. The browser's own
 *  smooth scroll is short and fixed (~300ms) whatever the distance, which is
 *  what felt abrupt; this takes longer the further it goes, within 450-900ms.
 *  Instant under prefers-reduced-motion. Resolves when it lands. */
function glideBy(dy: number): Promise<void> {
  const start = window.scrollY;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    window.scrollTo(0, start + dy);
    return Promise.resolve();
  }
  const duration = Math.min(900, Math.max(450, 350 + Math.abs(dy) * 0.25));
  const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
  return new Promise((resolve) => {
    const t0 = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - t0) / duration);
      window.scrollTo(0, start + dy * ease(t));
      if (t < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  });
}

/** Room around the clipped grid so the cards' 5% hover zoom isn't cut off at
 *  the clip edge. Applied as padding on the clipping wrapper. */
const CLIP_PAD = 8;

/** A grid that shows exactly its first row until `expanded`, then animates
 *  open to the full height.
 *
 *  Every card is always rendered; the wrapper is clipped with max-height.
 *  The first row's height is MEASURED, not assumed, so "one row" is right at
 *  every breakpoint (2, 3, 4 or 6 across) with no column counts duplicated
 *  here. A ResizeObserver re-measures when the width changes a card's height.
 *  Cards hidden below the clip are made `inert`, so keyboard users can't tab
 *  into fighters they can't see. */
function ExpandableRow({ expanded, children }: { expanded: boolean; children: React.ReactNode }) {
  const gridRef = useRef<HTMLDivElement>(null);
  const [heights, setHeights] = useState<{ row: number; full: number } | null>(null);
  // `children` is a new array every render, so depend on how many there are
  const count = Children.count(children);

  useLayoutEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const measure = () => {
      const items = Array.from(grid.children) as HTMLElement[];
      if (items.length === 0) return;
      const firstTop = items[0].offsetTop;
      const firstRow = items.filter((el) => el.offsetTop === firstTop);
      const row = Math.max(...firstRow.map((el) => el.offsetHeight));
      const full = grid.scrollHeight;
      // only store a CHANGED measurement: a fresh object every time would
      // re-render, re-measure and loop forever
      setHeights((prev) => (prev && prev.row === row && prev.full === full ? prev : { row, full }));
      for (const el of items) el.inert = !expanded && el.offsetTop !== firstTop;
    };
    measure();
    // width changes (and late-loading fonts) change card heights; re-measure
    const ro = new ResizeObserver(measure);
    ro.observe(grid);
    return () => ro.disconnect();
  }, [expanded, count]);

  const target = heights ? (expanded ? heights.full : heights.row) + CLIP_PAD * 2 : undefined;
  return (
    <div
      className="-m-2 overflow-hidden motion-safe:transition-[max-height] motion-safe:duration-500 motion-safe:ease-in-out"
      style={{ maxHeight: target, padding: CLIP_PAD }}
    >
      <div ref={gridRef} className={GRID}>
        {children}
      </div>
    </div>
  );
}

function SkeletonGrid({ count }: { count: number }) {
  return (
    <div className={GRID} aria-hidden>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i}>
          <div className="aspect-[3/4] animate-pulse rounded-xl bg-zinc-900" />
          <div className="mt-3 border-l-2 border-zinc-800 pl-3">
            <div className="h-2 w-3/4 animate-pulse rounded bg-zinc-900" />
            <div className="mt-2 h-2 w-1/2 animate-pulse rounded bg-zinc-900" />
          </div>
          <div className="mt-3 flex gap-2">
            {[0, 1, 2].map((d) => (
              <div key={d} className="h-6 w-6 animate-pulse rounded-full bg-zinc-900" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function FightersPage() {
  const [fighters, setFighters] = useState<string[]>([]);
  const [browse, setBrowse] = useState<BrowseFighters | null>(null);
  const [error, setError] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [showFullCard, setShowFullCard] = useState(false);
  const [showAllGoats, setShowAllGoats] = useState(false);
  // which leaderboards are expanded, by key
  const [openBoards, setOpenBoards] = useState<Set<string>>(new Set());
  const toggleBoard = (key: string) =>
    setOpenBoards((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  useEffect(() => {
    getFighters()
      .then(setFighters)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load fighters"));
    getBrowseFighters()
      .then(setBrowse)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load fighters"));
  }, []);

  // Case-insensitive name filter. Typing swaps the sections for results.
  const q = query.trim().toLowerCase();
  const visible = q ? fighters.filter((name) => name.toLowerCase().includes(q)) : [];

  const nextCard = browse?.next_card;
  const eventSlug = nextCard?.event.event_link.split("/").filter(Boolean).pop();

  // One row until the user asks for the whole card. Bout order puts the main
  // event first, so that row always leads with it. The toggle shows whenever
  // the SMALLEST row (2, on phones) would hide someone — gating on the widest
  // row instead would strand fighters 3-6 on a phone with no way to see them.
  const canExpand = (nextCard?.fighters.length ?? 0) > 2;

  return (
    // wider than .page (640px): six cards across needs the room
    <div className="FightersPage mx-auto w-full max-w-6xl px-3 py-8 text-left sm:px-4">
      <h1>Fighters</h1>
      {error && <p className="error">{error}</p>}

      {/* capped: .fighter-search is width 100%, sized for the old 640px page */}
      <div className="max-w-xl">
        <input
          className="fighter-search"
          type="text"
          value={query}
          placeholder="Search fighters…"
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {q ? (
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
      ) : (
        <div className="mt-10 flex flex-col gap-14">
          {!browse && !error && (
            <>
              <section>
                <SectionHeading title="On the next card" />
                <SkeletonGrid count={6} />
              </section>
              <section>
                <SectionHeading title="The GOATs" />
                <SkeletonGrid count={6} />
              </section>
            </>
          )}

          {nextCard && nextCard.fighters.length > 0 && (
            // green frame: the live, this-week section, set apart from the
            // evergreen lists below (emerald-500, the top of the app's ramp)
            <section className="scroll-mt-6 rounded-xl border border-emerald-500/70 p-4 sm:p-5">
              <SectionHeading
                title="On the next card"
                meta={
                  <Link to={`/events/${eventSlug}`} className="hover:text-white">
                    {nextCard.event.title} ·{" "}
                    {new Date(nextCard.event.date * 1000).toLocaleDateString(undefined, {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                    })}
                  </Link>
                }
                action={
                  canExpand && (
                    <ShowAllToggle
                      expanded={showFullCard}
                      total={nextCard.fighters.length}
                      onToggle={() => setShowFullCard((v) => !v)}
                      accent="#10b981"
                    />
                  )
                }
              />
              <ExpandableRow expanded={showFullCard}>
                {nextCard.fighters.map((f) => (
                  <FighterCard key={f.name} fighter={f} />
                ))}
              </ExpandableRow>
              {showFullCard && <CloseDot accent="#10b981" onClose={() => setShowFullCard(false)} />}
            </section>
          )}

          {browse && browse.top_careers.length > 0 && (
            // gold frame for the GOATs — the app's gold (#ffd75e, the
            // aged-well and Dream Fights accent), set against the green of
            // the this-week section above
            <section className="scroll-mt-6 rounded-xl border border-[#ffd75e]/70 p-4 sm:p-5">
              <SectionHeading
                title="The GOATs"
                meta="ranked by career score"
                action={
                  browse.top_careers.length > 2 && (
                    <ShowAllToggle
                      expanded={showAllGoats}
                      total={browse.top_careers.length}
                      onToggle={() => setShowAllGoats((v) => !v)}
                      accent="#ffd75e"
                    />
                  )
                }
              />
              <ExpandableRow expanded={showAllGoats}>
                {browse.top_careers.map((f, i) => (
                  <FighterCard key={f.name} fighter={f} rank={i + 1} />
                ))}
              </ExpandableRow>
              {showAllGoats && <CloseDot accent="#ffd75e" onClose={() => setShowAllGoats(false)} />}
            </section>
          )}

          {/* the fun lists — red frames, the app's own colour, so they read as
              one family under the green (this week) and gold (all time) */}
          {browse?.leaderboards
            .filter((board) => board.fighters.length > 0)
            .map((board) => (
              <section key={board.key} className="scroll-mt-6 rounded-xl border border-[#d33a2c]/70 p-4 sm:p-5">
                <SectionHeading
                  title={board.title}
                  meta={board.meta}
                  action={
                    board.fighters.length > 2 && (
                      <ShowAllToggle
                        expanded={openBoards.has(board.key)}
                        total={board.fighters.length}
                        onToggle={() => toggleBoard(board.key)}
                        accent="#d33a2c"
                      />
                    )
                  }
                />
                <ExpandableRow expanded={openBoards.has(board.key)}>
                  {board.fighters.map((f, i) => (
                    <FighterCard key={f.name} fighter={f} rank={i + 1} />
                  ))}
                </ExpandableRow>
                {openBoards.has(board.key) && (
                  <CloseDot accent="#d33a2c" onClose={() => toggleBoard(board.key)} />
                )}
              </section>
            ))}
        </div>
      )}
    </div>
  );
}
