import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AuthError,
  getBalance,
  getRoom,
  getRoomLeaderboard,
  joinRoom,
  type LeaderboardRow,
  type RoomDetail,
} from "../api";
import { CoinIcon } from "../components/CoinIcon";
import { RoomCover } from "../components/RoomCover";
import { closesIn } from "../lib/rooms";
import { errorMessage } from "../lib/errorMessage";
import "../rooms.css";

/** Payout split shown next to the top three ranks — mirrors the settle engine. */
const PAYOUT_SHARES = ["60%", "30%", "10%"];

/** Rank colors: gold / silver / bronze-ish orange, then muted. */
const RANK_COLORS = ["text-[#ffd75e]", "text-zinc-300", "text-orange-400"];

export default function RoomDetailPage() {
  const { roomId } = useParams();
  const id = Number(roomId);
  const navigate = useNavigate();

  const [room, setRoom] = useState<RoomDetail | null>(null);
  const [board, setBoard] = useState<LeaderboardRow[] | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [joinError, setJoinError] = useState("");
  const [joining, setJoining] = useState(false);
  const [reloadKey, setReloadKey] = useState(0); // bump to refetch after a join

  useEffect(() => {
    let cancelled = false; // that glitch remember
    setLoading(true);
    setError("");

    (async () => {
      try {
        const [detail, bal] = await Promise.all([getRoom(id), getBalance()]); // room id and balance from backend server
        // the leaderboard endpoint is member-only (403 otherwise),
        // so only ask for it once we know we're in the room
        const rows = detail.is_member ? await getRoomLeaderboard(id) : null;
        if (!cancelled) {
          setRoom(detail);
          setBalance(bal);
          setBoard(rows);
        }
        // counter when user picks a room when another room is loading
      } catch (e) {
        if (e instanceof AuthError) return navigate("/login"); //token expire or no log in
        if (!cancelled) setError(errorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id, navigate, reloadKey]);

  async function handleJoin() {
    setJoinError("");
    setJoining(true);
    try {
      await joinRoom(id); // wait to join room first
      setReloadKey((k) => k + 1); // pot, members, board and balance all changed
    } catch (e) {
      if (e instanceof AuthError) return navigate("/login");
      setJoinError(errorMessage(e));
    } finally {
      setJoining(false);
    }
  }

  if (loading) {
    return (
      <div className="w-full px-6 py-8 text-left">
        <div className="mx-auto max-w-3xl" aria-hidden>
          <div className="h-36 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900" />
          <div className="mt-6 h-40 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900" />
          <div className="mt-6 h-24 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900" />
        </div>
      </div>
    );
  }

  if (error || !room) {
    return (
      <div className="w-full px-6 py-8 text-left">
        <div className="mx-auto max-w-3xl">
          <p className="error">{error || "Room not found"}</p>
          <Link to="/rooms" className="text-sm text-zinc-400 underline hover:text-white">
            ← Back to the lobby
          </Link>
        </div>
      </div>
    );
  }

  const closing = closesIn(room.closes_at);
  const closed = closing === "closed";
  const short = room.entry_fee - (balance ?? 0); // coins missing to afford the buy-in

  return (
    <div className="w-full px-6 py-8 text-left">
      <div className="mx-auto max-w-3xl">
        <Link to="/rooms" className="text-sm text-zinc-400 hover:text-white">
          ← Lobby
        </Link>

        {/* banner: the room's generated cover, full width */}
        <div className="mt-3 overflow-hidden rounded-xl border border-zinc-800">
          <RoomCover seed={room.id} className="h-32 w-full sm:h-40" />
        </div>

        {/* title + badge + owner */}
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <h1 className="m-0 text-lg uppercase sm:text-2xl">{room.name}</h1>
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] tracking-widest ${
              room.is_public
                ? "border-orange-500/60 text-orange-400"
                : "border-zinc-600 text-zinc-400"
            }`}
          >
            {room.is_public ? "PUBLIC" : "PRIVATE"}
          </span>
        </div>
        <div className="mt-1 text-sm text-zinc-400">
          by{" "}
          <Link
            to={`/users/${room.owner_id}`}
            className="text-zinc-300 underline-offset-2 hover:text-red-400 hover:underline"
          >
            {room.owner_name}
          </Link>
        </div>

        {/* THE POT — hero of the page */}
        <div className="mt-8 rounded-xl border border-[#ffce4f33] bg-[#ffce4f0a] px-6 py-8 text-center">
          <div className="text-[10px] tracking-[0.3em] text-zinc-400">POT</div>
          <div className="mt-4 flex items-center justify-center gap-4">
            <CoinIcon size={36} className="shrink-0" />
            <span
              style={{ fontFamily: "var(--font-display)" }}
              className="text-4xl text-[#ffd75e] sm:text-5xl"
            >
              {room.pot.toLocaleString()}
            </span>
          </div>
          <div className="mt-4 text-xs text-zinc-500">
            split 60 / 30 / 10 between the top three when the room closes
          </div>
        </div>

        {/* readouts, same style as the lobby rows */}
        <div className="mt-6 grid grid-cols-3 gap-3">
          {[
            {
              label: "ENTRY",
              value:
                room.entry_fee === 0 ? "FREE" : room.entry_fee.toLocaleString(),
              gold: room.entry_fee > 0,
            },
            { label: "PLAYERS", value: String(room.member_count), gold: false },
            {
              label: "CLOSES",
              value: closed ? "CLOSED" : closing.toUpperCase(),
              gold: false,
            },
          ].map((r) => (
            <div
              key={r.label}
              className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-4 text-center"
            >
              <div className="text-[9px] tracking-widest text-red-400">{r.label}</div>
              <div
                style={{ fontFamily: "var(--font-display)" }}
                className={`mt-2 text-xs ${r.gold ? "text-[#ffd75e]" : "text-zinc-300"}`}
              >
                {r.value}
              </div>
            </div>
          ))}
        </div>

        {/* join block */}
        <div className="mt-8">
          {room.is_member ? (
            <span
              style={{ fontFamily: "var(--font-display)" }}
              className="inline-block rounded-lg border border-[#ffce4f66] bg-[#ffce4f14] px-4 py-3 text-[11px] text-[#ffd75e]"
            >
              ▸ YOU'RE IN
            </span>
          ) : closed ? ( //if closed
            <p className="text-sm text-zinc-500">
              This room is closed — no new entries.
            </p>
          ) : (
            <>
              <button
                onClick={handleJoin}
                disabled={joining || short > 0}
                className="rounded-lg bg-red-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {joining
                  ? "Joining…"
                  : room.entry_fee === 0
                    ? "Join — free"
                    : `Join for ${room.entry_fee.toLocaleString()} coins`}
              </button>
              {balance !== null && (
                <p className="mt-2 flex items-center gap-1.5 text-xs text-zinc-400">
                  You have <CoinIcon size={11} />{" "}
                  <span className="text-[#ffd75e]">{balance.toLocaleString()}</span>
                  {short > 0 && (
                    <span className="text-red-400">
                      — you need {short.toLocaleString()} more to enter
                    </span>
                  )}
                </p>
              )}
            </>
          )}
          {joinError && <p className="error text-sm">{joinError}</p>}
        </div>

        {/* leaderboard (members) or member list (outsiders) */}
        <div className="mt-10">
          <div className="mb-3 text-[10px] tracking-[0.3em] text-zinc-400">
            {room.is_member ? "LEADERBOARD" : "PLAYERS"}
          </div>

          {room.is_member && board ? (
            board.length === 0 ? (
              <p className="text-sm text-zinc-500">
                No settled picks yet — the board fills in as fights get results.
              </p>
            ) : (
              <ol className="flex flex-col gap-2">
                {board.map((row, i) => (
                  <li
                    key={row.id}
                    className="flex items-center gap-4 rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3"
                  >
                    <span
                      style={{ fontFamily: "var(--font-display)" }}
                      className={`w-8 shrink-0 text-xs ${RANK_COLORS[i] ?? "text-zinc-500"}`}
                    >
                      {i + 1}
                    </span>
                    <Link
                      to={`/users/${row.id}`}
                      className="min-w-0 flex-1 truncate text-sm text-white underline-offset-2 hover:text-red-400 hover:underline"
                    >
                      {row.name}
                    </Link>
                    {i < PAYOUT_SHARES.length && (
                      <span className="shrink-0 rounded-full border border-[#ffce4f66] px-2 py-0.5 text-[9px] tracking-widest text-[#ffd75e]">
                        {PAYOUT_SHARES[i]}
                        <span className="max-sm:hidden"> POT</span>
                      </span>
                    )}
                    <span className="shrink-0 text-xs text-zinc-400">
                      {row.correct}/{row.settled}
                    </span>
                    <span
                      style={{ fontFamily: "var(--font-display)" }}
                      className="w-20 shrink-0 text-right text-[11px] text-[#ffd75e]"
                    >
                      {row.points} PTS
                    </span>
                  </li>
                ))}
              </ol>
            )
          ) : room.members.length === 0 ? (
            <p className="text-sm text-zinc-500">No one has joined yet — be the first.</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {room.members.map((m) => (
                  <Link
                    key={m.id}
                    to={`/users/${m.id}`}
                    className="rounded-full border border-zinc-700 px-3 py-1 text-xs text-zinc-300 transition-colors hover:border-red-500/60 hover:text-white"
                  >
                    {m.name}
                  </Link>
                ))}
              </div>
              <p className="mt-3 text-xs text-zinc-500">
                Join the room to see its leaderboard.
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
