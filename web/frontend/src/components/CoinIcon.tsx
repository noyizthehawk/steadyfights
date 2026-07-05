/** Pixel-art gold coin (replaces the 🪙 emoji — SVG renders identically on
 *  every platform and scales crisply). Drawn on an 8x8 grid with crispEdges
 *  so it matches the Press Start 2P pixel aesthetic. Decorative: the coin
 *  amount next to it carries the meaning, so it's aria-hidden. */
export function CoinIcon({ size = 14, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 8 8"
      shapeRendering="crispEdges"
      aria-hidden
      className={className}
    >
      {/* coin body (pixel circle) */}
      <path d="M2 0h4v1H2z M1 1h6v1H1z M0 2h8v4H0z M1 6h6v1H1z M2 7h4v1H2z" fill="#ffce4f" />
      {/* top-left highlight */}
      <path d="M2 1h2v1H2z M1 2h1v2H1z" fill="#ffe9a3" />
      {/* bottom shade */}
      <path d="M1 5h1v1H1z M2 6h4v1H2z M6 5h1v1H6z" fill="#c99b2e" />
      {/* slot */}
      <rect x="3" y="2" width="1" height="4" fill="#c99b2e" />
    </svg>
  );
}
