import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getTotw, type Totw, type TotwPlayer } from "../api";

/** Team of the Week: the newest week's five best performances (win or lose),
 *  as black-and-gold FIFA-style cards. The big number is the fighter's CAREER
 *  score, with the arrow showing how much that one fight moved it. */

const GOLD = "#ffd75e";
const DISPLAY = { fontFamily: "var(--font-display)" } as const;
const RUNDOWN = { fontFamily: "var(--font-rundown)" } as const;
const MONO = { fontFamily: "var(--mono)" } as const;

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function Delta({ value, size = "text-[11px]" }: { value: number | null; size?: string }) {
  if (value === null) return <span className="text-[8px] text-zinc-400" style={DISPLAY}>NEW</span>;
  if (value === 0) return <span className={`${size} text-zinc-400`} style={MONO}>±0</span>;
  const up = value > 0;
  return (
    <span className={`${size} ${up ? "text-emerald-400" : "text-[#ff7a6b]"}`} style={MONO}>
      {up ? "▲" : "▼"}
      {Math.abs(value)}
    </span>
  );
}

/** A stat in a gold ring — the card's version of the app's score dots. */
function Ring({ label, value, delta, title }: { label: string; value: number; delta?: number | null; title: string }) {
  return (
    <div className="flex flex-col items-center gap-1" title={title}>
      <div className="flex items-center gap-1">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-full border-[1.5px] text-[12px] font-semibold tabular-nums text-white"
          style={{ ...MONO, borderColor: GOLD }}
        >
          {value}
        </span>
        {delta !== undefined && <Delta value={delta} size="text-[10px]" />}
      </div>
      <span className="text-[9px] tracking-wider text-zinc-500" style={MONO}>{label}</span>
    </div>
  );
}

/** Flat on purpose — solid black, solid gold frame with a thin inner frame
 *  (the FIFA double border), one solid divider, two typefaces: pixel for the
 *  number and name, mono for everything else. No gradients except the one
 *  that lets the cut-out headshot sit on the black. */
function TotwCard({ p }: { p: TotwPlayer }) {
  const to = `/fighters/${encodeURIComponent(p.fighter)}/career`;
  const result = [p.won ? "W" : "L", p.method].filter(Boolean).join(" ");
  return (
    <Link
      to={to}
      className="relative block aspect-[3/4.4] overflow-hidden rounded-lg border-2 bg-black"
      style={{ borderColor: GOLD }}
      aria-label={`${p.fighter}, career score ${p.career_score}`}
    >
      {/* inner frame */}
      <div className="pointer-events-none absolute inset-[5px] z-10 rounded-[4px] border" style={{ borderColor: `${GOLD}59` }} />

      {/* headshot, right-weighted; the only gradient seats it on the black */}
      <div className="absolute inset-x-0 top-0 h-[60%]">
        {p.image_url ? (
          <img src={p.image_url} alt="" loading="lazy" className="ml-auto h-full w-[80%] object-cover object-top" />
        ) : (
          <div className="flex h-full items-center justify-end pr-[20%] text-2xl text-zinc-800" style={DISPLAY} aria-hidden>
            {initials(p.fighter)}
          </div>
        )}
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_55%,#000_100%)]" />
      </div>

      {/* rating stack, top-left — the FIFA corner */}
      <div className="absolute left-3.5 top-3.5 z-10 flex flex-col items-start gap-1.5">
        <span className="text-[26px] leading-none" style={{ ...DISPLAY, color: GOLD }}>{p.career_score}</span>
        <Delta value={p.career_delta} />
        <span className="text-[7px]" style={{ ...DISPLAY, color: GOLD }}>TOTW</span>
        {p.flag_url && (
          <img src={p.flag_url} alt={p.country ?? ""} title={p.country ?? undefined} className="mt-0.5 h-3 w-auto" />
        )}
      </div>

      {/* name plate */}
      <div className="absolute inset-x-0 bottom-0 z-10 px-4 pb-4">
        <div className="line-clamp-2 text-center text-[9px] uppercase leading-relaxed sm:text-[10px]" style={{ ...DISPLAY, color: GOLD }}>
          {p.fighter}
        </div>
        <div className="mt-1 truncate text-center text-[10px] text-zinc-400" style={MONO}>
          {result} vs {p.opponent}
        </div>
        <div className="my-2.5 h-px w-full" style={{ background: `${GOLD}59` }} />
        <div className="flex items-start justify-center gap-5">
          <Ring label="NIGHT" value={Math.round(p.night)} title="Performance in this fight" />
          <Ring label="FORM" value={p.form} delta={p.form_delta} title="Form rating after this fight, and the change" />
        </div>
      </div>
    </Link>
  );
}

export function TeamOfTheWeek() {
  const [totw, setTotw] = useState<Totw | null>(null);
  useEffect(() => {
    getTotw().then(setTotw).catch(() => {});
  }, []);
  if (!totw || totw.team.length === 0) return null;

  const week = new Date(totw.week_end + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const events = totw.events.map((e) => e.split(":")[0].trim()).join(" · ");

  return (
    <section className="mx-auto max-w-6xl pb-12 text-left">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="!m-0 !text-[12px] !leading-none sm:!text-[13px]" style={{ ...DISPLAY, color: GOLD }}>
          TEAM OF THE WEEK
        </h2>
        <span className="text-xs italic text-zinc-500" style={RUNDOWN}>
          {events} · {week}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-5">
        {totw.team.map((p) => (
          <TotwCard key={p.fighter} p={p} />
        ))}
      </div>
    </section>
  );
}
