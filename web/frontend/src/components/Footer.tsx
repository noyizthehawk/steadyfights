import { Link } from "react-router-dom";

// Minimal, seamless footer — no border or background, so it reads as part of the
// page. One row: brand (left) · nav (center) · copyright (right).
export default function Footer() {
  return (
    <footer className="mt-auto w-full px-6 py-6">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 text-xs text-zinc-500 sm:flex-row sm:justify-between">
        {/* left */}
        <span className="font-semibold tracking-wide text-zinc-400">STEADYFIGHTS</span>

        {/* center */}
        <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
          <Link to="/predictor" className="transition-colors hover:text-white">Bout Brain</Link>
          <Link to="/prediction-game" className="transition-colors hover:text-white">Casual Checker</Link>
          <Link to="/rooms" className="transition-colors hover:text-white">Rooms</Link>
          <Link to="/leaderboard" className="transition-colors hover:text-white">Leaderboard</Link>
        </nav>

        {/* right */}
        <span>© {new Date().getFullYear()} STEADYCORPORATION</span>
      </div>

      {/* legal — kept, but subtle so the footer stays seamless */}
      <p className="mx-auto mt-4 max-w-6xl text-center text-[10px] leading-relaxed text-zinc-600">
        Coins are for entertainment only and cannot be redeemed for cash or prizes. Not affiliated with UFC®.
      </p>
    </footer>
  );
}
