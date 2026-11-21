import { useEffect, useState } from "react";
import { getIntro, type Intro } from "../api";
import { DotLink } from "./DotLink";

/** The logged-in landing greeting, as a red-corner card instead of
 *  "Welcome back, X". Deliberately minimal — no caps, no italics:
 *
 *      ┃ steadfastnoya                    ← pixel display font
 *      ┃ #12 · 34–21                      ← mono
 *      ┃ UFC 330 · Sat · 4 of 13 picked   ← hidden on an off week
 *        ●
 *        Finish card                      ← only when there's something to do
 *
 *  The card line follows the calendar and what the user has done. */

const FACE = { fontFamily: "var(--font-rundown)" } as const;
const MONO = { fontFamily: "var(--mono)" } as const;

function statLine(intro: Intro): string {
  if (intro.settled === 0) return "Debut";
  const record = `${intro.correct}–${intro.settled - intro.correct}`;
  return intro.rank ? `#${intro.rank} · ${record}` : `Unranked · ${record}`;
}

function when(unix: number): string {
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const date = new Date(unix * 1000);
  const days = Math.round((day(date) - day(new Date())) / 86_400_000);
  if (days <= 0) return "Tonight";
  if (days === 1) return "Tomorrow";
  if (days < 7) return date.toLocaleDateString(undefined, { weekday: "short" });
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function cardLine(next: Intro["next"]): { parts: string[]; link?: string } | null {
  if (!next || next.phase === "past") return null; // off week: say nothing
  const name = next.title.split(":")[0].trim(); // "UFC 330: A vs B" → "UFC 330"

  if (next.phase === "in_progress") {
    if (next.picked === 0) return { parts: [name, "Live", "no picks"] };
    if (next.settled === 0) return { parts: [name, "Live", `${next.picked} picks in`], link: "Your card" };
    return { parts: [name, "Live", `${next.correct} of ${next.settled} right`], link: "Your card" };
  }

  const head = [name, when(next.date)];
  if (next.picked === 0) return { parts: [...head, "no picks yet"], link: "Make picks" };
  if (next.picked < next.fights) return { parts: [...head, `${next.picked} of ${next.fights} picked`], link: "Finish card" };
  return { parts: [...head, "card full"] };
}

export function RingIntro({ username }: { username: string }) {
  const [intro, setIntro] = useState<Intro | null>(null);
  useEffect(() => {
    getIntro().then(setIntro).catch(() => {}); // the name alone still works as a greeting
  }, []);

  const card = intro ? cardLine(intro.next) : null;

  return (
    <div className="max-w-full text-left" style={FACE}>
      <div className="ring-in border-l-2 border-[#d33a2c] pl-4">
        {/* h1 for the page outline; the overrides undo the global pixel-font h1.
            Mono = scorecard / stat-sheet feel, and lines up with the record. */}
        <h1
          className="!m-0 !text-base !leading-snug !tracking-normal text-white sm:!text-xl"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {username}
        </h1>
        <p className="mt-2.5 text-sm text-zinc-500" style={MONO}>{intro ? statLine(intro) : " "}</p>
        {/* the next card is the third line of the same block; with no card
            scheduled there's nothing worth saying, so the line just isn't there */}
        {card && (
          <p className="ring-in mt-1 text-sm text-zinc-400" style={{ animationDelay: "120ms" }}>
            {card.parts.map((p, i) => (
              <span key={i}>
                {i > 0 && <span className="px-1.5 text-zinc-700">·</span>}
                <span className={i === 0 ? "text-zinc-200" : undefined}>{p}</span>
              </span>
            ))}
          </p>
        )}
      </div>

      {card?.link && (
        <div className="ring-in mt-4 pl-[18px]" style={{ animationDelay: "200ms" }}>
          <DotLink to="/prediction-game" label={card.link} />
        </div>
      )}
    </div>
  );
}
