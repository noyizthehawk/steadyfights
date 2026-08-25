import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getUserProfile, inviteFriend, AuthError, type UserProfile } from "../api";
import { Avatar } from "../components/Avatar";

// same theme as the old card: label a user from their winrate
function casualLabel(winrate: number | null) {
  if (winrate === null) return { text: "Unranked", cls: "bg-zinc-700 text-zinc-300" };
  if (winrate >= 60) return { text: "Killer", cls: "bg-green-600 text-white" };
  return { text: "Casual", cls: "bg-[#d33a2c] text-white" };
}

// one KPI tile — uniform so the stats row reads as a set
function Stat({ value, label, accent = false }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-center">
      <div className={`text-2xl font-bold tabular-nums ${accent ? "text-[#d33a2c]" : "text-white"}`}>
        {value}
      </div>
      <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-zinc-500">{label}</div>
    </div>
  );
}

export default function ProfilePage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string>("");
  const [inviteMsg, setInviteMsg] = useState(""); // feedback for the invite button

  useEffect(() => {
    if (!userId) return;
    getUserProfile(Number(userId))
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"));
  }, [userId]);

  async function handleInvite() {
    if (!profile) return;
    setInviteMsg("");
    try {
      await inviteFriend({ user_id: profile.id });
      setInviteMsg("Invite sent");
    } catch (e) {
      if (e instanceof AuthError) navigate("/login");
      else setInviteMsg(e instanceof Error ? e.message : "Could not invite");
    }
  }

  if (error) return <p className="w-full px-6 py-10 text-center text-red-400">{error}</p>;
  if (!profile) return <p className="w-full px-6 py-10 text-center text-zinc-500">Loading…</p>;

  const label = casualLabel(profile.stats.winrate);
  const { stats, world_rank } = profile;

  return (
    <div className="w-full px-4 py-8 sm:px-6">
      {/* one centered card with EQUAL padding on all sides */}
      <div className="mx-auto max-w-2xl space-y-8 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 sm:p-8">

        {/* ── header: avatar · identity · action ── */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <Avatar url={profile.avatar_url} name={profile.name} size={80} />

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-2xl font-bold text-white sm:text-3xl">{profile.name}</h1>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${label.cls}`}>
                {label.text}
              </span>
            </div>
            {profile.member_since && (
              <p className="mt-1 text-xs text-zinc-500">
                Member since{" "}
                {new Date(profile.member_since * 1000).toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "long",
                })}
              </p>
            )}
          </div>

          <div className="shrink-0 sm:self-center">
            <button
              onClick={handleInvite}
              className="w-full rounded-lg bg-[#d33a2c] px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 sm:w-auto"
            >
              Add Friend
            </button>
            {inviteMsg && (
              <p className="mt-1.5 text-center text-xs text-zinc-400 sm:text-right">{inviteMsg}</p>
            )}
          </div>
        </header>

        {/* ── KPI row ── */}
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat accent value={stats.winrate === null ? "—" : `${stats.winrate}%`} label="Win rate" />
          <Stat value={`${stats.correct}/${stats.settled}`} label="Correct" />
          <Stat value={String(stats.total_picks)} label="Picks" />
          <Stat
            value={world_rank ? `#${world_rank.rank}` : "—"}
            label={world_rank ? `of ${world_rank.total_ranked}` : "Unranked"}
          />
        </section>

        {/* ── recent form + streak ── */}
        {profile.recent_form.length > 0 && (
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Recent form
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              {profile.recent_form.map((r, idx) => (
                <span
                  key={idx}
                  title={r === "W" ? "Win" : "Loss"}
                  aria-label={r === "W" ? "Win" : "Loss"}
                  className={`flex h-8 w-8 items-center justify-center rounded-md text-xs font-bold text-white ${
                    r === "W" ? "bg-green-600" : "bg-zinc-700"
                  }`}
                >
                  {r}
                </span>
              ))}
              {profile.current_streak && (
                <span className="ml-1 text-sm text-zinc-400">
                  {profile.current_streak.count}-{profile.current_streak.type} streak
                </span>
              )}
            </div>
          </section>
        )}

        {/* ── best night ── */}
        {profile.best_event && (
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Best night
            </h2>
            <div className="rounded-xl border border-zinc-800 bg-zinc-800/50 p-4">
              <div className="font-semibold text-white">{profile.best_event.title}</div>
              <div className="mt-0.5 text-sm text-zinc-400">
                {profile.best_event.correct} of {profile.best_event.of} correct ·{" "}
                {profile.best_event.winrate}%
              </div>
            </div>
          </section>
        )}

        {/* ── footer: predictions · friends ── */}
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-zinc-800 pt-5 text-sm">
          {profile.events_count > 0 ? (
            <Link
              to={`/users/${profile.id}/events`}
              className="font-medium text-[#d33a2c] transition-opacity hover:opacity-80"
            >
              View predictions →
            </Link>
          ) : (
            <span className="text-zinc-500">No predictions yet</span>
          )}
          <span className="text-zinc-400">
            {profile.friends_count} friend{profile.friends_count === 1 ? "" : "s"}
          </span>
        </footer>
      </div>
    </div>
  );
}
