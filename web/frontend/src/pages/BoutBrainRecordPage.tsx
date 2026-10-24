import { useEffect, useState } from "react";
import { getBoutBrainPicks, type BoutBrainEvent, type BoutBrainPicks } from "../api";
import { ScoreBands, bandClimb } from "../components/ScoreBands";
import { DotLink } from "../components/DotLink";
import { inWords } from "../components/BoutBrainRecord";

/** Every pick in Bout Brain's record: past fights it never trained on,
 *  grouped by event, newest first. Each event opens (the app's dot) into its
 *  fights in the same layout as a user's predicted card — picked fighter in
 *  white, ✓ / ✗ between the two corners. Misses are shown like everything
 *  else; that's the point. */
export default function BoutBrainRecordPage() {
  const [data, setData] = useState<BoutBrainPicks | null>(null);
  const [error, setError] = useState("");
  // the newest event starts open so the page shows a card straight away
  const [open, setOpen] = useState<Set<string>>(new Set());

  useEffect(() => {
    getBoutBrainPicks()
      .then((d) => {
        setData(d);
        if (d.by_event[0]) setOpen(new Set([key(d.by_event[0])]));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  const toggle = (k: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return next;
    });

  const fmt = (n: number) => n.toLocaleString();
  const month = (d: string) =>
    new Date(d + "T00:00:00").toLocaleDateString(undefined, { month: "short", year: "numeric" });
  const right = data ? data.by_event.reduce((s, e) => s + e.correct, 0) : 0;

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 text-left">
      <DotLink to="/predictor" label="Bout Brain" />
      <h1>The record</h1>
      {error && <p className="error">{error}</p>}
      {!data && !error && <div className="text-sm text-zinc-500">Loading…</div>}

      {data && (
        <>
          {/* Headline: the confident picks — knowing which picks to trust is
              the product. The overall rate sits right under it, never hidden. */}
          {data.confident.accuracy !== null && (
            <div className="mt-8 text-base italic text-zinc-200" style={{ fontFamily: "var(--font-rundown)" }}>
              When Bout Brain is confident, it's right{" "}
              <span className="font-semibold not-italic text-emerald-400">{inWords(data.confident.accuracy)}</span>.
            </div>
          )}
          <div className="mb-3 mt-3 flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <div className="text-4xl leading-none text-white" style={{ fontFamily: "var(--font-display)" }}>
              {data.confident.accuracy ?? data.accuracy}
              <span className="text-[#d33a2c]">%</span>
            </div>
            <div className="text-sm text-zinc-400">
              {data.confident.accuracy !== null
                ? `on its 70+ picks (${fmt(data.confident.fights)} fights)`
                : `${fmt(right)} of ${fmt(data.fights)} correct`}
            </div>
          </div>
          <div className="mb-3 text-sm text-zinc-400">
            Every pick: <span className="font-semibold text-zinc-200">{data.accuracy}%</span> ·{" "}
            {fmt(right)} of {fmt(data.fights)} correct · {fmt(data.events)} events
          </div>
          <div
            className="mb-8 border-l-2 border-[#d33a2c] pl-3 text-xs italic leading-relaxed text-zinc-500"
            style={{ fontFamily: "var(--font-rundown)" }}
          >
            Every fight from {month(data.from)} to {month(data.to)}. Bout Brain learned only from the{" "}
            {fmt(data.trained_on)} fights before these, so each pick here was made blind. Draws and
            no contests are left out; misses are not.
          </div>

          {/* the score's record by band — the climb is the selling point */}
          <section className="mb-10 rounded-xl border border-zinc-800 bg-black p-4 sm:p-5">
            <div className="mb-4 border-l-2 border-[#d33a2c] pl-3">
              <h3
                className="m-0 text-[11px] uppercase leading-relaxed text-white"
                style={{ fontFamily: "var(--font-display)" }}
              >
                How the score has performed
              </h3>
              <div className="text-sm italic text-zinc-300" style={{ fontFamily: "var(--font-rundown)" }}>
                The surer it is, the more it's right: {bandClimb(data.bands)}
              </div>
            </div>
            <ScoreBands bands={data.bands} />
            <div
              className="mt-4 border-t border-zinc-900 pt-3 text-xs italic leading-relaxed text-zinc-500"
              style={{ fontFamily: "var(--font-rundown)" }}
            >
              Every decided fight on every card, {month(data.from)} – {month(data.to)}:{" "}
              {fmt(data.fights)} picks, none hand-picked, none seen in training. The rows add up to the
              whole record below.
            </div>
          </section>

          <ul className="m-0 list-none space-y-2 p-0">
            {data.by_event.map((ev) => (
              <EventRow key={key(ev)} ev={ev} open={open.has(key(ev))} onToggle={() => toggle(key(ev))} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

const key = (e: BoutBrainEvent) => `${e.event}|${e.date}`;

function EventRow({ ev, open, onToggle }: { ev: BoutBrainEvent; open: boolean; onToggle: () => void }) {
  const rate = Math.round((ev.correct / ev.fights) * 100);
  return (
    <li className="rounded-xl border border-zinc-800 bg-black">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="group/dot flex w-full cursor-pointer items-center gap-4 p-3 text-left sm:p-4"
      >
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-zinc-100">{ev.event}</div>
          <div className="text-xs italic text-zinc-500" style={{ fontFamily: "var(--font-rundown)" }}>
            {new Date(ev.date + "T00:00:00").toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </div>
        </div>
        {/* the event's score, green when it beat a coin flip */}
        <div className="shrink-0 text-right">
          <div className={`text-sm font-bold tabular-nums ${rate > 50 ? "text-emerald-400" : "text-zinc-400"}`}>
            {ev.correct}/{ev.fights}
          </div>
          <div className="text-[10px] tabular-nums text-zinc-600">{rate}%</div>
        </div>
        {/* the app's dot: quiet when shut, red with its ring when open */}
        <span
          aria-hidden
          className="block h-2.5 w-2.5 shrink-0 rounded-full transition-all duration-200 group-hover/dot:scale-110"
          style={{
            background: open ? "#d33a2c" : "rgba(255,255,255,.25)",
            boxShadow: open ? "0 0 0 4px #d33a2c33" : "none",
          }}
        />
      </button>

      {open && (
        <ul className="m-0 list-none space-y-2 border-t border-zinc-900 p-3 sm:p-4">
          {ev.picks.map((p, i) => {
            const pickedA = p.pick === p.fighter_a;
            return (
              <li key={i} className="flex items-center justify-between gap-3 rounded-lg bg-zinc-900 px-3 py-2.5">
                <Corner name={p.fighter_a} picked={pickedA} won={p.winner === p.fighter_a} />
                <div className="shrink-0 text-center">
                  <div className={`text-sm font-bold ${p.correct ? "text-emerald-500" : "text-[#d33a2c]"}`}>
                    {p.correct ? "✓" : "✗"}
                  </div>
                  <div className="text-[10px] tabular-nums text-zinc-600" title="how sure it was of its pick">
                    {p.confidence}%
                  </div>
                </div>
                <Corner name={p.fighter_b} picked={!pickedA} won={p.winner === p.fighter_b} right />
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}

/** One side of a fight: the picked fighter in white, the other grey; the
 *  actual winner gets a small "won" tag. */
function Corner({ name, picked, won, right = false }: { name: string; picked: boolean; won: boolean; right?: boolean }) {
  return (
    <div className={`min-w-0 flex-1 ${right ? "text-right" : ""}`}>
      <div className={`break-words text-sm font-semibold ${picked ? "text-white" : "text-zinc-500"}`}>{name}</div>
      <div className="text-[10px] uppercase tracking-wider">
        {picked && <span className="text-zinc-400">pick</span>}
        {picked && won && <span className="text-zinc-600"> · </span>}
        {won && <span className="text-emerald-500">won</span>}
      </div>
    </div>
  );
}
