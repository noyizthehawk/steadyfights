import { useEffect, useState } from "react";
import { getBoutBrainRecord, type BoutBrainPick, type BoutBrainRecord as RecordData } from "../api";
import { ScoreBands } from "./ScoreBands";
import { DotLink } from "./DotLink";

/** Bout Brain's advert, sized for the sidebar above Dream fights: its record
 *  on past fights it never trained on, then a feed of those picks to scroll.
 *
 *  The "ingesting" theatre is UI only: the accuracy counts up while a status
 *  line walks through what the model does, and the feed's rows stream in one
 *  by one. Every number and pick is real (the
 *  temporal hold-out, /api/bout-brain/record), misses included.
 *
 *  Hides itself if the record can't be loaded. Under reduced motion it shows
 *  the final state with nothing moving. */
export function BoutBrainRecord({ heading }: { heading?: React.ReactNode }) {
  const [record, setRecord] = useState<RecordData | null>(null);

  useEffect(() => {
    getBoutBrainRecord().then(setRecord).catch(() => setRecord(null));
  }, []);

  // the heading comes in from the page so it vanishes with the card
  if (!record) return null;
  return (
    <div>
    {heading}
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-black">
      <Numbers record={record} />
      {/* the score's climb, band by band — the selling point, compact */}
      <div className="border-t border-zinc-900 px-4 py-3">
        <div
          className="mb-2 text-[11px] italic text-zinc-400"
          style={{ fontFamily: "var(--font-rundown)" }}
        >
          The surer it is, the more it's right
        </div>
        <ScoreBands bands={record.bands} compact />
      </div>
      <Feed picks={record.picks} />
      {/* to the full record: the app's dot, words under it */}
      <div className="flex justify-end border-t border-zinc-900 px-4 py-2.5">
        <DotLink to="/bout-brain/record" label="Every pick" />
      </div>
    </div>
    </div>
  );
}

const REDUCED =
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const COUNT_MS = 2200;
const ease = (t: number) => 1 - (1 - t) ** 3;

function Numbers({ record }: { record: RecordData }) {
  // 0 -> 1 over COUNT_MS; drives the counter, the bar and the status line
  const [progress, setProgress] = useState(REDUCED ? 1 : 0);

  useEffect(() => {
    if (REDUCED) return;
    let raf = 0;
    const t0 = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - t0) / COUNT_MS);
      setProgress(t);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, []);

  const done = progress >= 1;
  const fmt = (n: number) => n.toLocaleString();
  // The headline is the CONFIDENT picks, not the overall rate: every honest
  // model sits in the low 60s across every fight (the coin flips included);
  // what makes Bout Brain useful is knowing which picks to trust.
  const sure = record.confident;
  const headline = sure.accuracy ?? record.accuracy;
  const stages = [
    `Loading ${fmt(record.fights)} past fights`,
    "Reading strikes & takedowns",
    "Updating Elo ratings",
    "Scoring picks vs results",
  ];
  const stage = done
    ? `Checked against ${fmt(record.events)} events`
    : stages[Math.min(stages.length - 1, Math.floor(progress * stages.length))];

  return (
    <div className="p-4">
      {/* the hook in words, then the number behind it */}
      {sure.accuracy !== null && (
        <div className="mb-2 text-sm italic leading-snug text-zinc-200" style={{ fontFamily: "var(--font-rundown)" }}>
          When Bout Brain is confident, it's right{" "}
          <span className="font-semibold not-italic text-emerald-400">{inWords(sure.accuracy)}</span>.
        </div>
      )}
      <div
        className="text-3xl leading-none text-white tabular-nums"
        style={{ fontFamily: "var(--font-display)" }}
        aria-label={`${headline}% right when confident`}
      >
        {(headline * ease(progress)).toFixed(1)}
        <span className="text-[#d33a2c]">%</span>
      </div>
      <div className="mt-2 text-xs italic text-zinc-500" style={{ fontFamily: "var(--font-rundown)" }}>
        {sure.accuracy !== null
          ? `on its 70+ picks (${fmt(sure.fights)} past fights it never trained on)`
          : `right on ${fmt(record.fights)} past fights it never trained on`}
      </div>
      {/* the overall rate, in plain sight but not the headline */}
      {sure.accuracy !== null && (
        <div className="mt-1 text-[11px] text-zinc-600">
          Every pick: {record.accuracy}% across {fmt(record.fights)} fights
        </div>
      )}
      <div className="mt-2 text-xs italic text-zinc-500" style={{ fontFamily: "var(--font-rundown)" }}>
        We are the best and most honest model on the market.
      </div>

      {/* "ingesting": a hairline filling with the count, and what it's on */}
      <div className="mt-3 h-[2px] w-full overflow-hidden rounded-full bg-zinc-800" aria-hidden>
        <div className="h-full bg-[#d33a2c]" style={{ width: `${progress * 100}%` }} />
      </div>
      <div className="mt-1.5 flex items-center gap-1.5 font-mono text-[10px] text-zinc-500" aria-hidden>
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${done ? "bg-emerald-500" : "animate-pulse bg-[#d33a2c]"}`} />
        {stage}
        {!done && "…"}
      </div>
    </div>
  );
}

/** A rate as a fan would say it: 78% -> "4 out of 5", 91% -> "9 out of 10".
 *  Rounded to the nearest fifth, or tenth at the top end (where a fifth would
 *  round up to "5 out of 5"). Shared with the record page. */
export function inWords(pct: number): string {
  if (pct >= 87.5) return `${Math.round(pct / 10)} out of 10`;
  return `${Math.round(pct / 20)} out of 5`;
}

/** Rows that stream in on load; the rest are already there to scroll to. */
const STREAMED_ROWS = 14;

function Feed({ picks }: { picks: BoutBrainPick[] }) {
  if (picks.length === 0) return null;
  return (
    <div className="relative border-t border-zinc-900 bg-zinc-950">
      <ul
        className="m-0 h-56 list-none overflow-y-auto overscroll-contain p-0 py-1 font-mono text-[10.5px]"
        aria-label="Bout Brain's latest past picks"
      >
        {picks.map((p, i) => (
          <li
            key={i}
            className="bb-row-in flex items-center gap-2 px-4 py-1.5"
            // one after another, as if being read in
            style={{ animationDelay: `${300 + Math.min(i, STREAMED_ROWS) * 90}ms` }}
            title={`${p.event} · ${p.fighter_a} vs ${p.fighter_b} · picked ${p.pick} (${p.confidence}%) · ${p.winner} won`}
          >
            <span className="shrink-0 text-zinc-600">{p.date.slice(2).replaceAll("-", ".")}</span>
            {/* the pick is the bright name */}
            <span className="min-w-0 flex-1 truncate text-zinc-500">
              <Name name={p.fighter_a} picked={p.pick === p.fighter_a} />
              <span className="text-zinc-700"> v </span>
              <Name name={p.fighter_b} picked={p.pick === p.fighter_b} />
            </span>
            <span className="shrink-0 tabular-nums text-zinc-600">{p.confidence}%</span>
            <span
              className={`w-3 shrink-0 text-center font-bold ${p.correct ? "text-emerald-500" : "text-[#d33a2c]"}`}
              aria-label={p.correct ? "right" : "wrong"}
            >
              {p.correct ? "✓" : "✗"}
            </span>
          </li>
        ))}
      </ul>
      {/* soft edges top and bottom */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-5 bg-gradient-to-b from-zinc-950 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-6 bg-gradient-to-t from-zinc-950 to-transparent" />
    </div>
  );
}

function Name({ name, picked }: { name: string; picked: boolean }) {
  return <span className={picked ? "text-zinc-100" : undefined}>{lastName(name)}</span>;
}

/** "Jon Jones" -> "Jones", "Raul Rosas Jr." -> "Rosas Jr." — enough for a
 *  narrow terminal line. */
export function lastName(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length <= 1) return name;
  const suffix = /^(jr\.?|sr\.?|ii|iii|iv)$/i.test(parts[parts.length - 1]);
  return suffix && parts.length > 2 ? parts.slice(-2).join(" ") : parts[parts.length - 1];
}
