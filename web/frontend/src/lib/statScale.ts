/** p2-p98 of each tale-of-the-tape stat, measured over fighters with 5+ UFC bouts.
 *
 *  Shared by the profile's tale of the tape (FighterDetailsCard) and the
 *  Fighters page cards (FighterCard), so a stat fills and colours the same
 *  everywhere. The backend picks each card's "best metric" with the SAME
 *  numbers — STAT_BOUNDS in part_2/career.py. Change both together.
 *
 *  The point of the bar is to show where someone sits IN THE DATA, so every
 *  bound is measured rather than chosen. Two decisions behind that:
 *
 *  p2-p98, not the tighter p10-p90 these started on. At p90 the top of striking
 *  accuracy was 54%, so a genuinely very good 57% filled the track completely
 *  and read as perfect — and 29 fighters with real careers, Aspinall at 67%
 *  among them, were indistinguishable. Only the outer 2% clamp now.
 *
 *  And 5+ bouts, not everyone. A fighter who went 1-for-1 on takedowns shows
 *  100% accuracy; 22 of those sat at the top of the unrestricted distribution
 *  and would have set the ceiling for the whole roster. Five fights is enough
 *  that a rate means something.
 *
 *  Percentages are deliberately not scaled 0-100: nobody lands 0% or 100% of
 *  their strikes, so a raw percentage bar sits mid-track for everyone and
 *  separates nothing.
 */
export const STAT_SCALE: Record<string, [number, number]> = {
  str_acc: [31, 61],
  str_def: [39, 68],
  slpm: [1.3, 6.4],
  sapm: [1.5, 6.3],
  td_acc: [14, 81],
  td_def: [23, 100],
  td_avg: [0.2, 5.1],
  sub_avg: [0.1, 2.6],
};

/** Stats where a LOWER number is better. */
export const INVERTED_STATS = new Set(["sapm"]);

/** Where a value sits in its own range, as a 0-100 figure the Bar can take. */
export function scaledStat(value: number | null | undefined, key: string): number | null {
  if (value == null) return null;
  const [low, high] = STAT_SCALE[key];
  const t = (value - low) / (high - low);
  // Absorbing fewer strikes is better, so its bar has to fill the other way
  // or a durable fighter would read as the worst on the card.
  return Math.max(0, Math.min(100, (INVERTED_STATS.has(key) ? 1 - t : t) * 100));
}
