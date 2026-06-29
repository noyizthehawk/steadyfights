import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getUserProfile, inviteFriend, AuthError, type UserProfile } from "../api";

// same theme as the old card: label a user from their winrate
function casualLabel(winrate: number | null) {
  if (winrate === null) return { text: "Unranked", cls: "bg-zinc-700 text-zinc-300" };
  if (winrate >= 60) return { text: "Killer", cls: "bg-green-600 text-white" };
  return { text: "Casual", cls: "bg-[#d33a2c] text-white" };
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
      setInviteMsg("Invite sent ✓");
    } catch (e) {
      if (e instanceof AuthError) navigate("/login");
      else setInviteMsg(e instanceof Error ? e.message : "Could not invite");
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!profile) return <p className="page text-zinc-500">Loading…</p>;

  const label = casualLabel(profile.stats.winrate);

  return (
    <div className="page w-full px-6 pt-8 pb-12 border border-zinc-700 rounded-lg">
      {/* header */}
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <h1 className="text-3xl font-bold text-white">{profile.name}</h1>
        <span className={`inline-block rounded-full px-3 py-0.5 text-xs font-semibold ${label.cls}`}>
          {label.text}
        </span>
        {profile.world_rank && (
          <span className="text-sm text-zinc-400">
            Rank #{profile.world_rank.rank} of {profile.world_rank.total_ranked}
          </span>
        )}
        <button
          onClick={handleInvite}
          className="ml-auto rounded bg-[#d33a2c] px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
        >
          Add Friend
        </button>
      </div>
      {inviteMsg && <p className="mb-4 text-xs text-zinc-400">{inviteMsg}</p>}

      {profile.member_since && (
        <p className="mb-6 text-xs text-zinc-500">
          Member since {new Date(profile.member_since * 1000).toLocaleDateString()}
        </p>
      )}

      {/* headline stats */}
      <div className="mb-6 flex flex-wrap items-baseline gap-8">
        <div>
          <div className="text-4xl font-bold text-[#d33a2c]">
            {profile.stats.winrate === null ? "—" : `${profile.stats.winrate}%`}
          </div>
          <div className="text-xs text-zinc-400">win rate</div>
        </div>
        <div className="text-sm text-zinc-400">
          {profile.stats.correct} of {profile.stats.settled} correct
          {" · "}
          {profile.stats.total_picks} picks made
        </div>
      </div>

      {/* recent form + streak */}
      {profile.recent_form.length > 0 && (
        <div className="mb-6">
          <div className="mb-2 text-xs uppercase tracking-wide text-zinc-500">Recent form</div>
          <div className="flex items-center gap-2">
            {profile.recent_form.map((r, idx) => (
              <span
                key={idx}
                className={`flex h-7 w-7 items-center justify-center rounded text-xs font-bold text-white ${
                  r === "W" ? "bg-green-600" : "bg-zinc-600"
                }`}
              >
                {r}
              </span>
            ))}
            {profile.current_streak && (
              <span className="ml-2 text-sm text-zinc-400">
                on a {profile.current_streak.count}-{profile.current_streak.type} streak
              </span>
            )}
          </div>
        </div>
      )}

      {/* best event */}
      {profile.best_event && (
        <div className="mb-6 rounded-lg bg-zinc-800 p-4">
          <div className="text-xs uppercase tracking-wide text-zinc-500">Best night</div>
          <div className="mt-1 font-semibold text-white">{profile.best_event.title}</div>
          <div className="text-sm text-zinc-400">
            {profile.best_event.correct} of {profile.best_event.of} correct ·{" "}
            {profile.best_event.winrate}%
          </div>
        </div>
      )}

      {/* footer counts */}
      <div className="flex gap-6 text-sm text-zinc-400">
        <Link to={`/users/${profile.id}/events`} className="hover:text-white">
          {profile.events_count} Latest Predictions{profile.events_count === 1 ? "" : "s"} →
        </Link>
        <span>{profile.friends_count} Friend{profile.friends_count === 1 ? "" : "s"}</span>
      </div>
    </div>
  );
}
