import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  me,
  getUpcomingEvents,
  getLeaderboard,
  getNews,
  getVideos,
  getNotable,
  getNextConsensus,
  type MeResponse,
  type UFCEvent,
  type LeaderboardRow,
  type NewsArticle,
  type Video,
  type NotableUser,
  type NextConsensus,
} from "../api";
import { EventTileMini } from "../components/EventTileMini";
import { NewsTile } from "../components/NewsTile";
import { VideoTile } from "../components/VideoTile";
import { NotableUsers } from "../components/NotableUsers";
import { PunditConsensus } from "../components/PunditConsensus";


const FEATURES: { title: string; blurb: string; to: string }[] = [
  {
    title: "Bout Brain",
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
  // undefined = auth not checked yet; null = logged out; object = logged in
  const [user, setUser] = useState<MeResponse | null | undefined>(undefined);
  const [events, setEvents] = useState<UFCEvent[]>([]);
  const [board, setBoard] = useState<LeaderboardRow[]>([]);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [notable, setNotable] = useState<NotableUser[]>([]);
  const [consensus, setConsensus] = useState<NextConsensus | null>(null);

  useEffect(() => {
    me().then(setUser).catch(() => setUser(null));
    // all public + already cheap/cached — fetch in parallel, each its own cache
    getUpcomingEvents().then(setEvents).catch(() => {});
    getLeaderboard().then((b) => setBoard(b.slice(0, 5))).catch(() => {});
    getNews("UFC").then(setNews).catch(() => {});
    getVideos().then(setVideos).catch(() => {});
    getNotable().then(setNotable).catch(() => {});
    getNextConsensus().then(setConsensus).catch(() => {});
  }, []);

  return (
    <div className="w-full px-4 py-8 text-[#e7e7ea]">
      <section className="mx-auto max-w-3xl py-12 text-center">
        {user ? (
          <>
            <h1 className="mb-4 text-4xl font-bold text-white sm:text-5xl">
              Welcome back, <span className="text-[#d33a2c]">{user!.username}</span>.
            </h1>
            <p className="mx-auto max-w-xl text-lg text-zinc-400">
            </p>
          </>
        ) : user === null ? (
          <>
            <h1 className="mb-4 text-4xl font-bold text-white sm:text-5xl">
              Predict the fights. <span className="text-[#d33a2c]">Are you a casual?</span>
            </h1>
            <p className="mx-auto mb-8 max-w-xl text-lg text-zinc-400">
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
                Try Bout Brain
              </Link>
            </div>
          </>
        ) : null}
      </section>

      {/* Body: events (left) · feature tiles (center) · leaderboard (right) */}
      <section className="mx-auto flex max-w-6xl flex-col gap-6 pb-16 lg:flex-row">
        {/* Left — small event tiles, 2 per row */}
        <aside className="lg:w-80 lg:shrink-0">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">
            Upcoming Events
          </h2>
          {events.length === 0 ? (
            <p className="text-sm text-zinc-500">No upcoming events.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {/* events come sorted soonest-first, so index 0 is the immediate
                  next event — the only one that gets the pulsing glow. */}
              {events.map((ev, idx) => (
                <EventTileMini key={ev.event_link} event={ev} highlight={idx === 0} />
              ))}
            </div>
          )}
        </aside>

        {/* Center — pundit consensus, the 4 category tiles, then prediction videos */}
        <div className="flex flex-1 flex-col gap-6">
          {/* Pundit consensus for the next main event (hides itself if unavailable) */}
          <PunditConsensus data={consensus} />

          <div className="grid content-start gap-4 sm:grid-cols-2">
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
          </div>

          {/* Prediction videos — wide 16:9 carousel under the feature grid */}
          {videos.length > 0 && (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
                  Prediction/Reaction Videos
                </h2>
              </div>
              <VideoTile videos={videos} />
            </div>
          )}
        </div>

        {/* Right — top-5 leaderboard snapshot + scrollable news tile */}
        <aside className="space-y-6 lg:w-64 lg:shrink-0">
          <div className="rounded-lg border border-zinc-800 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
                Top 5
              </h2>
              <Link to="/leaderboard" className="text-xs text-[#d33a2c] hover:underline">
                Full board →
              </Link>
            </div>
            {board.length === 0 ? (
              <p className="text-sm text-zinc-500">No ranked players yet.</p>
            ) : (
              <ol className="space-y-1">
                {board.map((row, i) => (
                  <li
                    key={row.id}
                    className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-zinc-800"
                  >
                    <span className="flex items-center gap-2 truncate">
                      <span className="w-4 shrink-0 text-right font-bold text-zinc-500">{i + 1}</span>
                      <Link to={`/users/${row.id}`} className="truncate text-white hover:underline">
                        {row.name}
                      </Link>
                    </span>
                    <span className="shrink-0 font-semibold tabular-nums text-[#d33a2c]">
                      {row.winrate != null ? `${row.winrate}%` : "—"}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          {/* Notable users — curated showcase (e.g. MMA YouTubers) */}
          <NotableUsers users={notable} />

          {/* News — scroll through like IG posts */}
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">
              News
            </h2>
            <NewsTile articles={news} />
          </div>
        </aside>
      </section>

      {/* Closing CTA — only when confirmed logged OUT (null), never while
          auth is still loading (undefined) or when logged in. */}
      {user === null && (
        <section className="mx-auto max-w-2xl pb-20 text-center">
          <h2 className="mb-4 text-2xl font-bold text-white">Ready to make your picks?</h2>
          <Link
            to="/signup"
            className="inline-block rounded-lg bg-[#d33a2c] px-6 py-3 font-semibold text-white transition-transform hover:scale-105"
          >
            Create an account
          </Link>
        </section>
      )}
    </div>
  );
}
