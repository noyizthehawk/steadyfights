import { Link } from "react-router-dom";
import type { FighterCardData } from "../api";
import { CareerScoreChip, ScoreDot } from "./FighterTags";
import { Bar } from "./Meters";
import { scaledStat } from "../lib/statScale";

/** First letter of the first and last name: "Jon Jones" -> "JJ". */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

/** A fighter on the Fighters page: picture, name, the three overall cells, and
 *  one bar for whatever they do best.
 *
 *  Same tile language as the rooms lobby and the homepage event tiles — the
 *  picture leads, the caption hangs off the red rule. Picture, name and caption
 *  are separate links to the profile, because the Commons credit is its own
 *  <a> and an <a> can't nest inside another. */
export function FighterCard({ fighter, rank }: { fighter: FighterCardData; rank?: number }) {
  const to = `/fighters/${encodeURIComponent(fighter.name)}/career`;
  const debut = fighter.overall_perf === null;
  const credit = fighter.image_credit;
  const highlight = fighter.highlight;

  return (
    <article className="group text-left">
      <Link to={to} className="block">
        {/* Dark radial backdrop: UFC headshots are cut-outs on transparency,
            so this is what sits behind them. object-top keeps the head in
            frame for both the upper-body event crops and full-body shots. */}
        <div className="relative aspect-[3/4] w-full overflow-hidden rounded-xl bg-[radial-gradient(ellipse_at_top,#3f1d1d_0%,#18181b_70%)] shadow-lg transition-transform duration-200 group-hover:scale-105">
          {fighter.image_url ? (
            <img
              src={fighter.image_url}
              alt={fighter.name}
              loading="lazy"
              className="h-full w-full object-cover object-top"
            />
          ) : (
            <div
              className="flex h-full w-full items-center justify-center text-2xl text-zinc-600"
              style={{ fontFamily: "var(--font-display)" }}
              aria-hidden
            >
              {initials(fighter.name)}
            </div>
          )}
          {/* leaderboard position: flat dark chip, P2 like every other label */}
          {rank !== undefined && (
            <span
              className="absolute left-2 top-2 rounded bg-black/75 px-1.5 py-1 text-[9px] leading-none text-white"
              style={{ fontFamily: "var(--font-display)" }}
            >
              #{rank}
            </span>
          )}
        </div>
      </Link>

      {/* Commons licences require a credit; UFC images carry none */}
      {credit && (
        <a
          href={credit.url}
          target="_blank"
          rel="noreferrer"
          className="mt-1 block truncate text-[9px] leading-tight text-zinc-600 hover:text-zinc-400"
        >
          Photo: {credit.author ?? "Wikimedia Commons"} · {credit.license}
        </a>
      )}

      {/* a <div> carries the margin — index.css's unlayered `p { margin: 0 }`
          would eat it on a <p> */}
      <div className="mt-3 border-l-2 border-[#d33a2c] pl-3">
        {/* name + career score, the event page's pairing (name, then chip) */}
        <div className="flex items-start justify-between gap-2">
          <Link
            to={to}
            className="line-clamp-2 min-w-0 break-words text-[10px] uppercase leading-relaxed text-zinc-200 hover:text-white"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {fighter.name}
          </Link>
          {fighter.career_score !== null && <CareerScoreChip value={fighter.career_score} />}
        </div>
        <div
          className="mt-1 flex items-center gap-1.5 text-xs italic text-zinc-500"
          style={{ fontFamily: "var(--font-rundown)" }}
        >
          {/* the flag normally sits beside FORM in the cells row below; a debut
              card has no cells row, so it rides the caption instead */}
          {debut && fighter.flag_url && (
            <img
              src={fighter.flag_url}
              alt={fighter.country ?? ""}
              title={fighter.country ?? undefined}
              className="h-3 w-auto shrink-0 rounded-[2px]"
            />
          )}
          <span className="truncate capitalize">
            {debut ? "UFC debut" : [fighter.record, fighter.division].filter(Boolean).join(" · ")}
          </span>
        </div>
      </div>

      {!debut && (
        <>
          {/* overall performance cells — the event page's badges and colours,
              so a 72 is the same green everywhere in the app */}
          <div className="mt-3 flex items-end gap-2">
            <ScoreDot
              label="PERF"
              value={fighter.overall_perf!}
              title={`Performance ${Math.round(fighter.overall_perf!)} — how well they perform once opponent quality is accounted for`}
            />
            <ScoreDot
              label="OPP"
              value={fighter.overall_opp!}
              title={`Opposition ${Math.round(fighter.overall_opp!)} — quality of opponents faced across the career`}
            />
            <ScoreDot
              label="FORM"
              value={fighter.recent_perf!}
              title={`Form ${Math.round(fighter.recent_perf!)} — last 3 fights, latest counts most`}
            />
            {/* flag right beside FORM. Same 24px height as the dots and
                bottom-aligned with them (items-end), so it reads as one more
                badge in the row. Only fighters from a scraped event card have
                one; legends don't. */}
            {fighter.flag_url && (
              <img
                src={fighter.flag_url}
                alt={fighter.country ?? ""}
                title={fighter.country ?? undefined}
                className="h-6 w-auto shrink-0 rounded-[3px] border border-zinc-700"
              />
            )}
          </div>

          {/* their single best metric. Fill and colour come from scaledStat —
              the profile tale of the tape's own scaler — so this bar is
              identical to the same stat's bar on their profile. The header
              prints the real figure, hence Bar's own header is off; the
              percentile underneath says how that figure ranks. */}
          {/* on a leaderboard the bar is the list's stat — why they're on it.
              Same layout as the best-stat block below so the cards line up. */}
          {highlight && (
            <div className="mt-3">
              <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="truncate text-[10px] font-medium text-zinc-400">{highlight.label}</span>
                <span className="shrink-0 text-[11px] font-bold tabular-nums text-zinc-200">
                  {highlight.display}
                </span>
              </div>
              <Bar value={highlight.fill} label={highlight.label} max={100} showHeader={false} />
              {highlight.note && (
                <div className="mt-1 text-right text-[10px] text-zinc-400">{highlight.note}</div>
              )}
            </div>
          )}

          {!highlight && fighter.best_metric && (
            <div
              className="mt-3"
              title={`Their best stat — better than ${Math.floor(fighter.best_metric.percentile)}% of UFC fighters with 5+ fights`}
            >
              {/* Says outright that this is their standout, chosen from all
                  eight tale-of-the-tape stats — otherwise a lone bar looks
                  arbitrary. Same tiny uppercase as the PERF / OPP / RF labels. */}
              <div className="mb-1 text-[8px] font-bold uppercase leading-none tracking-wider text-zinc-500">
                Best stat
              </div>
              <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="truncate text-[10px] font-medium text-zinc-400">
                  {fighter.best_metric.label}
                </span>
                <span className="shrink-0 text-[11px] font-bold tabular-nums text-zinc-200">
                  {fighter.best_metric.display}
                </span>
              </div>
              <Bar
                value={scaledStat(fighter.best_metric.value, fighter.best_metric.key)}
                label={fighter.best_metric.label}
                max={100}
                showHeader={false}
              />
              {/* Always worded, never a bare number, so it can't be mistaken
                  for the 0-100 scores in the cells above. "Top X%" only reads
                  as praise in the top half; below that it says what it is. */}
              <div className="mt-1 text-right text-[10px] text-zinc-400">
                {fighter.best_metric.top_pct <= 50
                  ? `Top ${fighter.best_metric.top_pct}%`
                  : `Better than ${Math.floor(fighter.best_metric.percentile)}%`}
              </div>
            </div>
          )}
        </>
      )}
    </article>
  );
}
