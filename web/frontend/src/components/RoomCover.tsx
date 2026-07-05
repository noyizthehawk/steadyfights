import { mulberry32 } from "../lib/rooms";

/** Procedurally generated arcade cover, seeded by the room id.
 *  Same room -> same art forever; different rooms -> different art.
 *  Mirrored pixel grid (identicon-style): red + orange emblems with gold flecks on dark. */
export function RoomCover({ seed, className }: { seed: number; className?: string }) {
  const rand = mulberry32(seed || 1);

  const COLS = 10;
  const ROWS = 6;
  const CELL = 16; // viewBox is 160x96 (10x6 cells)
  const half = COLS / 2;

  // Build the left half, mirror each cell to the right — symmetry is what makes
  // random pixels read as a deliberate "emblem" instead of noise.
  const cells: { x: number; y: number; fill: string; o: number }[] = [];
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < half; x++) {
      if (rand() < 0.55) continue; // keep it sparse
      const roll = rand();
      const fill = roll < 0.6 ? "#dc2626" : roll < 0.85 ? "#f97316" : "#ffce4f";
      const o = 0.35 + rand() * 0.65;
      cells.push({ x, y, fill, o });
      cells.push({ x: COLS - 1 - x, y, fill, o }); // mirror
    }
  }

  const gid = `rc-${seed}`; // gradient ids must be unique per svg on the page
  return (
    <svg
      viewBox="0 0 160 96"
      className={className}
      preserveAspectRatio="xMidYMid slice"
      shapeRendering="crispEdges"
      aria-hidden
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2b0b0b" />
          <stop offset="100%" stopColor="#080202" />
        </linearGradient>
      </defs>
      <rect width="160" height="96" fill={`url(#${gid})`} />
      {cells.map((c, i) => (
        <rect
          key={i}
          x={c.x * CELL}
          y={c.y * CELL}
          width={CELL}
          height={CELL}
          fill={c.fill}
          opacity={c.o}
        />
      ))}
      {/* gold "floor" strip grounds the composition */}
      <rect y="92" width="160" height="4" fill="#ffce4f" opacity="0.25" />
    </svg>
  );
}
