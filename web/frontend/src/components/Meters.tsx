/** Radial and linear meters for the 0-100 career scores.
 *
 * Each of these is a single ratio against a fixed limit, which is a METER — not
 * a chart and not a pie. Magnitude is carried by the arc or bar LENGTH plus the
 * printed number, never by hue, so none of these depends on colour to be read.
 */

/** One hue, the brand red, on every meter.
 *
 * A green/amber/grey severity ramp was the obvious choice and the wrong one
 * here: it spends colour on something the mark already says. The arc length and
 * the printed number both carry magnitude, so recolouring by value adds nothing
 * and costs the page its identity — red is what makes this site look like
 * itself, and a wall of green rings looks like any other dashboard.
 *
 * It also sidesteps the ramp's real problem: amber and orange sit at ΔE 6.7,
 * which is below the threshold where normal colour vision can tell them apart
 * in a row of meters.
 */
const TRACK = "#1c1c1f";

/** Value ramp, shared by every meter on the page.
 *
 * Both the rings and the phase bars sit in rows of their own kind, so in both
 * cases the reader's actual question is "which of these is the strong one" —
 * and colour answers that faster than comparing four arc lengths does.
 *
 * Three steps, not four: amber and orange measured ΔE 6.7 apart, below what
 * normal colour vision separates when the marks sit next to each other.
 */
// The event page's palette (see FighterTags.tsx), interpolated.
//
// Those badges already teach a reader what a number looks like on this site —
// zinc for unremarkable, orange, amber, emerald at the top — so a second,
// unrelated ramp on the profile meant the same score wore two different
// colours depending on which page you were looking at. Same stops here, blended
// rather than stepped so every value still gets its own shade.
//
// Stops are positioned where FighterTags switches, not spread evenly, so the
// discrete badges and these meters agree at the boundaries.
const STOPS: [number, [number, number, number]][] = [
  [0.00, [0x52, 0x52, 0x5b]], // zinc-600
  [0.35, [0x52, 0x52, 0x5b]], // zinc-600  — flat below 35, "unremarkable"
  [0.50, [0xf9, 0x73, 0x16]], // orange-500
  [0.65, [0xfb, 0xbf, 0x24]], // amber-400
  [0.80, [0x10, 0xb9, 0x81]], // emerald-500
  [1.00, [0x34, 0xd3, 0x99]], // emerald-400 — the very top still separates
];

/** Colour at position `t` (0-1) along the ramp. */
function rampColor(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  let i = 0;
  while (i < STOPS.length - 2 && c > STOPS[i + 1][0]) i++;
  const [p0, a] = STOPS[i];
  const [p1, b] = STOPS[i + 1];
  const f = p1 === p0 ? 0 : (c - p0) / (p1 - p0);
  const mix = a.map((ch, k) => Math.round(ch + (b[k] - ch) * f));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

/** Where a value sits on the ramp.
 *
 * Absolute 0-100, matching the event page. Normalising to each metric's own
 * spread would use the gradient more fully, but it would also mean a 60 here
 * and a 60 on a fight card were different colours — and the whole point of
 * borrowing this palette is that they agree.
 */
function position(value: number, [low, high]: [number, number]): number {
  return (value - low) / (high - low);
}

const FULL: [number, number] = [0, 100];

/** Kept as named exports so a metric can take its own range later; both sit on
 *  the absolute scale for now so the profile and the event cards agree. */
export const RING_RANGE = {
  performance: FULL,
  strength: FULL,
};

/** Career score — same absolute scale as everything else. */
export const CAREER_RANGE: [number, number] = FULL;

/** Circular meter. `value` is 0-100; null renders an empty track. */
export function Ring({
  value,
  label,
  hint,
  delta,
  range = FULL,
  size = 76,
}: {
  value: number | null;
  label: string;
  hint?: string;
  /** Change against the career figure, for the "recent" rings. The pair only
   *  means something read together — a fighter climbing the division shows a
   *  low career number and a high recent one, and one being matched softly
   *  shows the reverse — so the gap is the thing worth stating outright
   *  instead of leaving the reader to subtract two rings. */
  delta?: number | null;
  range?: [number, number];
  size?: number;
}) {
  // Thin marks: a 6px stroke on a 76px ring reads as a measurement, where a
  // thick one reads as decoration.
  const stroke = 6;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value));
  const color = rampColor(position(pct, range));

  // Its own cell, defined by a fill rather than an outline. A border draws a
  // hard line around every metric and seven of them turn the panel into a
  // grid of boxes; a 3.5% white wash separates the cell from the page without
  // adding an edge, which is how most modern dark UIs handle a surface.
  return (
    <div className="relative flex flex-col items-center gap-1.5 rounded-xl bg-white/[0.035] transition-colors hover:bg-white/[0.06] p-3">
      {delta !== undefined && delta !== null && Math.abs(delta) >= 1 && (
        /* Top-right, out of the vertical stack: it is an annotation on the
           figure rather than another line of it. Direction is carried by the
           glyph as well as the colour, so it survives greyscale. Under a point
           of movement is noise, not a trend. */
        <span
          className="absolute right-1.5 top-1.5 text-[10px] font-semibold tabular-nums"
          style={{ color: delta > 0 ? "#34d399" : "#fb7185" }}
        >
          {delta > 0 ? "▲" : "▼"}{Math.abs(Math.round(delta))}
        </span>
      )}
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* Track is a dim step of the same neutral, so the unfilled portion
              still reads as part of the measurement rather than a hole. */}
          <circle
            cx={size / 2} cy={size / 2} r={r}
            fill="none" stroke={TRACK} strokeWidth={stroke}
          />
          {value !== null && (
            <circle
              cx={size / 2} cy={size / 2} r={r}
              fill="none" stroke={color} strokeWidth={stroke}
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - pct / 100)}
              className="transition-[stroke-dashoffset] duration-700 ease-out"
            />
          )}
        </svg>
        <span className="absolute inset-0 flex items-center justify-center">
          {/* Proportional figures, not tabular: tabular-nums gives every digit
              the width of a 0, which looks loose at display sizes. */}
          <span
            className="text-lg font-bold"
            style={{ color: value === null ? "#52525b" : color }}
          >
            {value === null ? "—" : Math.round(value)}
          </span>
        </span>
      </div>
      <span className="max-w-[7.5rem] text-center text-[10px] font-medium leading-tight text-zinc-400">
        {label}
      </span>
      {hint && (
        <span className="max-w-[8rem] text-center text-[10px] leading-tight text-zinc-500">
          {hint}
        </span>
      )}
    </div>
  );
}

/** Horizontal meter — used where several values are compared down a column,
 *  which a row of rings cannot do: bars share a baseline, rings don't. */
export function Bar({
  value,
  label,
  max = 100,
  /** Defaults to the fill's own scale. Width and colour MUST share it: they
   *  were split once — width on `max`, colour on a fixed 0-75 — and every bar
   *  past 75% of its range clamped to full green, so a 63%-filled track
   *  rendered as bright green as a 100% one. */
  range = [0, max],
  /** Suppress the built-in label/value row. For callers that already print
   *  their own figure above the track — without this they get two numbers, the
   *  real stat and this component's 0-100 scaled position. */
  showHeader = true,
}: {
  value: number | null;
  label: string;
  max?: number;
  range?: [number, number];
  showHeader?: boolean;
}) {
  // Width and colour take DIFFERENT inputs, deliberately.
  //
  // Width is the value as a share of its ceiling, so the fill is proportional.
  // Colour is the RAW value — the number printed beside it — because that is
  // what the thresholds describe. Colouring on the share made every bar green:
  // perf runs about 42-55 against a ceiling of 75, so even a poor 42 became 57%
  // and cleared the 60 mark.
  const pct = value === null ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  const color = rampColor(position(value ?? 0, range));
  return (
    <div>
      {showHeader && (
        <div className="mb-1 flex items-baseline justify-between gap-2">
          <span className="text-[10px] font-medium text-zinc-400">{label}</span>
          <span className="text-[11px] font-bold tabular-nums" style={{ color: value === null ? "#52525b" : color }}>
            {value === null ? "—" : Math.round(value)}
          </span>
        </div>
      )}
      {/* Square, not pill-shaped. A rounded cap on a 6px bar rounds away a
          couple of percent of the fill at both ends, so short values read
          longer than they are and the baseline stops being a straight edge. */}
      <div className="h-1.5" style={{ background: TRACK }}>
        <div
          className="h-full transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

/** The career score badge. Same ramp as every other meter, so a 70 here is the
 *  same shade as a 70 anywhere else on the page.
 *
 *  Dark text on the fill, not white: the ramp runs through yellow, and white on
 *  #ffd400 is about 1.3:1 — illegible. The fill is the only thing carrying the
 *  colour, so the text has to step out of its way.
 */
export function CareerScore({ value }: { value: number | null }) {
  const color = value === null ? "#3f3f46" : rampColor(position(value, CAREER_RANGE));
  return (
    <span
      title="Career quality (0-100)"
      className="inline-flex min-w-[3rem] shrink-0 items-center justify-center rounded-lg px-2.5 py-1.5 text-base font-bold"
      style={{ background: color, color: value === null ? "#a1a1aa" : "#0a0a0a" }}
    >
      {value === null ? "—" : Math.round(value)}
    </span>
  );
}

/** A plain figure with no meter — for counts and rates that have no fixed
 *  ceiling to measure against. A ring implies a limit; a fight count has none. */
export function Figure({ value, label, hint }: { value: string | number; label: string; hint?: string }) {
  return (
    <div className="relative flex flex-col items-center justify-center gap-1 rounded-xl bg-white/[0.035] transition-colors hover:bg-white/[0.06] p-3 text-center">
      <span className="text-xl font-bold text-white">{value}</span>
      <span className="text-[10px] font-medium leading-tight text-zinc-400">{label}</span>
      {hint && <span className="text-[10px] leading-tight text-zinc-500">{hint}</span>}
    </div>
  );
}
