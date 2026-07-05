// Helpers for the rooms lobby: deterministic randomness + countdown formatting.

/** Tiny seeded PRNG (mulberry32). Same seed -> same sequence of "random" numbers,
 *  which is how every room gets a unique cover that never changes between renders. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** The backend stores datetimes as NAIVE UTC, so closes_at arrives like
 *  "2026-08-01T18:00:00" with no timezone. new Date() would read that as LOCAL
 *  time (off by your UTC offset), so we append "Z" to force UTC parsing. */
export function parseServerDate(s: string): Date {
  const hasZone = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(s);
  return new Date(hasZone ? s : s + "Z");
}

/** "closes in" label for a room tile: "2d 4h", "5h 12m", "23m", or "closed".
 *  Computed once per render on purpose — no per-second ticker for a whole grid. */
export function closesIn(closesAt: string): string {
  const ms = parseServerDate(closesAt).getTime() - Date.now();
  if (ms <= 0) return "closed";
  const mins = Math.floor(ms / 60000);
  const days = Math.floor(mins / 1440);
  const hours = Math.floor((mins % 1440) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins % 60}m`;
  return `${mins}m`;
}
