import { Link } from "react-router-dom";

// Each card on the feature grid. `to` links straight into that feature so a
// visitor can try it before signing up.
const FEATURES: { title: string; blurb: string; to: string }[] = [
  {
    title: "Fight Predictor",
    blurb: "Pick two fighters and get ML-driven win probabilities, styles, and the edges that decide it.",
    to: "/predictor",
  },
  {
    title: "Pick'em Game",
    blurb: "Call upcoming UFC cards, lock your picks, and get scored automatically against the real results.",
    to: "/prediction-game",
  },
  {
    title: "Leaderboard & Friends",
    blurb: "Climb a global win-rate leaderboard and add friends to see who really knows the fight game.",
    to: "/leaderboard",
  },
  {
    title: "Career Analytics",
    blurb: "Opponent-adjusted career scores, phase-by-phase breakdowns, and an all-time Top Careers ranking.",
    to: "/top-career",
  },
];

export default function LandingPage() {
  return (
    <div className="page">
      {/* Hero */}
      <section className="mx-auto max-w-3xl py-16 text-center">
        <h1 className="mb-4 text-4xl font-bold text-white sm:text-5xl">
          Predict the fights. <span className="text-[#d33a2c]">Are you a casual?</span>
        </h1>
        <p className="mx-auto mb-8 max-w-xl text-lg text-zinc-400">
          A data-driven UFC playground with the best model on earth.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/signup"
            className="rounded-lg bg-[#d33a2c] px-6 py-3 font-semibold text-white transition-transform hover:scale-105"
          >
            Get started
          </Link>
          <Link
            to="/predictor"
            className="rounded-lg border border-zinc-700 px-6 py-3 font-semibold text-white transition-colors hover:bg-zinc-800"
          >
            Try the predictor
          </Link>
        </div>
      </section>

      {/* Feature grid */}
      <section className="mx-auto grid max-w-4xl gap-4 pb-16 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <Link
            key={f.title}
            to={f.to}
            className="rounded-lg bg-zinc-800 p-6 transition-transform hover:scale-[1.02] hover:bg-zinc-700"
          >
            <h2 className="mb-2 text-xl font-bold text-white">{f.title}</h2>
            <p className="text-sm text-zinc-400">{f.blurb}</p>
          </Link>
        ))}
      </section>

      {/* Closing CTA */}
      <section className="mx-auto max-w-2xl pb-20 text-center">
        <h2 className="mb-4 text-2xl font-bold text-white">Ready to make your picks?</h2>
        <Link
          to="/signup"
          className="inline-block rounded-lg bg-[#d33a2c] px-6 py-3 font-semibold text-white transition-transform hover:scale-105"
        >
          Create an account
        </Link>
      </section>
    </div>
  );
}
