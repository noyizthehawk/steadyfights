import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getLeaderboard, inviteFriend, AuthError, type LeaderboardRow } from "../api";

// ties into the "Casual Checker" theme — label a user from their winrate
function casualLabel(winrate: number | null) {
  if (winrate === null) return { text: "Unranked", cls: "bg-zinc-700 text-zinc-300" };
  if (winrate >= 60) return { text: "Killer", cls: "bg-green-600 text-white" };
  return { text: "Casual", cls: "bg-[#d33a2c] text-white" };
}

export default function UserCardPage() {
  // optional :start index from the URL (e.g. /users/3 when clicked from the leaderboard)
  const { start } = useParams<{ start?: string }>();
  const navigate = useNavigate();
  const [rows, setRows] = useState<LeaderboardRow[]>([]);
  const [error, setError] = useState<string>("");
  const [i, setI] = useState(Number(start) || 0); // index of the card currently shown
  const [inviteMsg, setInviteMsg] = useState(""); // feedback for the Add Friend button

  useEffect(() => {
    getLeaderboard()
      .then((data) => {
        setRows(data);
        // guard against an out-of-range start index
        if (data.length && Number(start) >= data.length) setI(0);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load users"));
  }, [start]);

  if (error) return <p className="error">{error}</p>;
  if (rows.length === 0) return <p className="page text-zinc-500">No ranked users yet.</p>;

  // wrap-around: % keeps the index inside [0, length). Clear any invite message on move.
  const prev = () => { setInviteMsg(""); setI((i - 1 + rows.length) % rows.length); };
  const next = () => { setInviteMsg(""); setI((i + 1) % rows.length); };

  const user = rows[i];
  const rank = i + 1;
  const label = casualLabel(user.winrate);

  async function handleAddFriend() {
    setInviteMsg("");
    try {
      await inviteFriend({ user_id: user.id });
      setInviteMsg("Invite sent ✓");
    } catch (e) {
      if (e instanceof AuthError) navigate("/login");
      else setInviteMsg(e instanceof Error ? e.message : "Could not invite");
    }
  }

  return (
    <div className="page flex flex-col items-center">
      <h1 className="mb-6 text-2xl font-bold text-white">Fighters' Records</h1>

      <div className="flex items-center gap-4">
        <button
          onClick={prev}
          aria-label="Previous"
          className="rounded-full bg-zinc-800 px-4 py-2 text-xl text-white hover:bg-zinc-700"
        >
          ◀
        </button>

        <div className="w-72 rounded-xl border border-zinc-700 bg-zinc-900 p-6 text-center shadow-2xl">
          <div className="text-sm font-bold text-zinc-500">#{rank}</div>
          <h2 className="mt-1 text-xl font-bold text-white">{user.name}</h2>

          <span className={`mt-2 inline-block rounded-full px-3 py-0.5 text-xs font-semibold ${label.cls}`}>
            {label.text}
          </span>

          <div className="mt-4 text-4xl font-bold text-[#d33a2c]">
            {user.winrate === null ? "—" : `${user.winrate}%`}
          </div>
          <div className="text-xs text-zinc-400">win rate</div>

          <div className="mt-4 flex justify-around text-sm text-white">
            <div>
              <div className="font-bold">{user.correct}/{user.settled}</div>
              <div className="text-xs text-zinc-400">settled</div>
            </div>
            <div>
              <div className="font-bold">{user.total_picks}</div>
              <div className="text-xs text-zinc-400">picks</div>
            </div>
          </div>

          <button
            onClick={handleAddFriend}
            className="mt-5 w-full rounded bg-[#d33a2c] py-2 text-sm font-semibold text-white hover:opacity-90"
          >
            Add Friend
          </button>
          {inviteMsg && <p className="mt-2 text-xs text-zinc-400">{inviteMsg}</p>}
        </div>

        <button
          onClick={next}
          aria-label="Next"
          className="rounded-full bg-zinc-800 px-4 py-2 text-xl text-white hover:bg-zinc-700"
        >
          ▶
        </button>
      </div>

      <p className="mt-4 text-xs text-zinc-500">{rank} of {rows.length}</p>
    </div>
  );
}
