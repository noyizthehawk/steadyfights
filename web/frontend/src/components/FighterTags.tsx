import ufcLogo from "../assets/ufc-logo.png";
import type { FighterTag } from "../api";

/** Colour for a 0-100 value. Green at the top, falling through amber and
 * orange to muted zinc.
 *
 * Deliberately stops short of red at the bottom: the app already spends red as
 * its accent (links, delete, the brand), so a red badge would read as "alert"
 * rather than "low". Muted zinc says "unremarkable" without shouting.
 *
 * Five steps, which is roughly as many as anyone can tell apart at 24px — the
 * number inside carries the precision.
 */
function tone(value: number): string {
  if (value >= 80) return "bg-emerald-500 text-zinc-900";
  if (value >= 65) return "bg-amber-400 text-zinc-900";
  if (value >= 50) return "bg-orange-500 text-zinc-900";
  if (value >= 35) return "bg-zinc-600 text-zinc-100";
  return "bg-zinc-700 text-zinc-400";
}

/** A labelled score: the abbreviation sits above its own dot, so each badge
 *  says what it is.
 *
 *  This is what replaces the legend. The two dots are the same shape, so
 *  without a label the only cue is ORDER — which a reader has to learn from
 *  somewhere else on the page, and can't learn at all on a phone where there
 *  is no hover.
 */
function ScoreDot({ label, value, title }: { label: string; value: number; title: string }) {
  return (
    <span className="flex flex-col items-center gap-0.5" title={title}>
      <span className="text-[8px] font-bold uppercase leading-none tracking-wider text-zinc-500">
        {label}
      </span>
      {/* White ring ties the two scored dots together as one kind of thing, and
          lifts the darker tones off the zinc-800 card they'd otherwise sink into. */}
      <span
        className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-white/70 text-[10px] font-bold tabular-nums ${tone(value)}`}
      >
        {Math.round(value)}
      </span>
    </span>
  );
}

/** The badges above a fighter's name: recent form, strength of opposition, and
 *  the fight count.
 *
 *  The count spells out "UFC fights" rather than sitting in a bare square. It's
 *  the one value with no 0-100 scale and no colour meaning, so naming it costs
 *  nothing and removes the last thing a reader has to guess at.
 */
export function FighterTags({
  tag,
  mirrored = false,
}: {
  tag: FighterTag | null | undefined;
  mirrored?: boolean;
}) {
  if (!tag) return null;
  // Mirrored reverses the ORDER too, not just the alignment, so the pair reads
  // symmetrically across the "vs" rather than both rows running left to right.
  // items-end so the pill's baseline lines up with the dots despite the labels
  // making the dot stacks taller.
  return (
    <div
      className={`mb-1 flex items-end gap-1.5 ${
        mirrored
          ? "justify-center sm:flex-row-reverse sm:justify-start"
          : "justify-center sm:justify-start"
      }`}
    >
      <ScoreDot
        label="RF"
        value={tag.recent_form}
        title={`Recent form ${tag.recent_form}/100 — last 5 fights (${tag.recent_record})`}
      />
      <ScoreDot
        label="SOO"
        value={tag.strength_iq}
        title={`Strength of opposition ${tag.strength_iq}/100 — quality of opponents faced`}
      />
      {/* Same label-above-value stack as the dots, with the logo standing in
          for the text label — so the three badges keep one rhythm and the
          count needs no words to explain itself. Still a SQUARE below, because
          a fight count is a fact rather than a grade and must not read as a
          score that happens to be uncoloured. */}
      <span className="flex flex-col items-center gap-0.5" title={`${tag.total_fights} UFC fights`}>
        <img src={ufcLogo} alt="UFC" className="h-4 w-4 shrink-0 rounded-[3px] object-contain" />
        <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-[4px] border border-zinc-700 bg-zinc-800 text-[10px] font-bold tabular-nums text-zinc-200">
          {tag.total_fights}
        </span>
      </span>
    </div>
  );
}

/** The career score, sat immediately after the fighter's name.
 *
 * A number rather than a dot: this is the headline figure and the difference
 * between 78 and 86 matters, which no colour swatch can carry.
 */
export function ScoreChip({ tag }: { tag: FighterTag | null | undefined }) {
  if (!tag) return null;
  return (
    <span
      title={`Career score ${tag.career_score}/100`}
      className={`inline-flex shrink-0 items-center justify-center rounded px-1.5 py-0.5 text-[11px] font-bold tabular-nums ${tone(tag.career_score)}`}
    >
      {Math.round(tag.career_score)}
    </span>
  );
}
