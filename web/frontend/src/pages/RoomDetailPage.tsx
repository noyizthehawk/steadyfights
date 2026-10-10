import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  AuthError,
  getBalance,
  getRoom,
  getRoomLeaderboard,
  joinRoom,
  reportRoomCover,
  uploadRoomCover,
  type LeaderboardRow,
  type RoomDetail,
} from "../api";
import { Avatar } from "../components/Avatar";
import { CoinIcon } from "../components/CoinIcon";
import { RoomCover } from "../components/RoomCover";
import { closesIn } from "../lib/rooms";
import { errorMessage } from "../lib/errorMessage";
import "../rooms.css";

/** Payout split by finishing place — mirrors split_pot in room_settlement.py:
 *  under 3 players the winner takes everything, otherwise 60/30/10. */
function payoutShares(players: number): string[] {
  return players < 3 ? ["100%"] : ["60%", "30%", "10%"];
}

/** Card heading, in the app's heading face (Press Start 2P, --font-display).
 *  No extra tracking: the pixel font is already ~1em per glyph, so wide
 *  tracking just pulls the letters apart. An <h3>, not <h2>: index.css styles
 *  h1/h2 outside any @layer (24px + margin), and unlayered CSS beats every
 *  Tailwind utility, so the size here would lose. */
function CardLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3
      className="m-0 text-[9px] uppercase leading-relaxed text-zinc-400"
      style={{ fontFamily: "var(--font-display)" }}
    >
      {children}
    </h3>
  );
}

/** Hairline card shell, same as the profile page's cards. */
const CARD = "rounded-lg border border-zinc-700 p-4";

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
  const [coverBusy, setCoverBusy] = useState(false);
  // CreateRoomPage lands here with a message if the room was made but the
  // cover upload failed — the owner can retry right on the banner
  const location = useLocation();
  const [coverMsg, setCoverMsg] = useState<string>(
    (location.state as { coverError?: string } | null)?.coverError ?? "",
  );

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

  async function handleCover(file: File) {
    setCoverMsg("");
    setCoverBusy(true);
    try {
      const { cover_url } = await uploadRoomCover(id, file);
      // patch locally — nothing else on the page changed, no need to refetch
      setRoom((r) => (r ? { ...r, cover_url, has_reported_cover: false } : r));
    } catch (e) {
      if (e instanceof AuthError) return navigate("/login");
      setCoverMsg(errorMessage(e));
    } finally {
      setCoverBusy(false);
    }
  }

  async function handleReport() {
    if (!window.confirm("Report this cover as inappropriate?")) return;
    setCoverMsg("");
    try {
      const { cover_removed } = await reportRoomCover(id);
      setRoom((r) =>
        r ? { ...r, has_reported_cover: true, cover_url: cover_removed ? null : r.cover_url } : r,
      );
      setCoverMsg(cover_removed ? "Thanks — that cover has been taken down." : "Thanks — we've flagged it.");
    } catch (e) {
      if (e instanceof AuthError) return navigate("/login");
      setCoverMsg(errorMessage(e));
    }
  }

  if (loading) {
    // same skeleton as the real layout: banner, then main column + 320px rail
    return (
      <div className="mx-auto w-full max-w-6xl px-3 py-8 text-left sm:px-4" aria-hidden>
        <div className="h-52 animate-pulse rounded-lg bg-zinc-900 sm:h-64" />
        <div className="mt-6 flex flex-col gap-5 lg:flex-row lg:items-start">
          <div className="h-64 flex-1 animate-pulse rounded-lg bg-zinc-900" />
          <div className="h-72 animate-pulse rounded-lg bg-zinc-900 lg:w-80" />
        </div>
      </div>
    );
  }

  if (error || !room) {
    return (
      <div className="mx-auto w-full max-w-6xl px-3 py-8 text-left sm:px-4">
        <p className="error">{error || "Room not found"}</p>
        <Link to="/rooms" className="text-sm text-zinc-400 underline hover:text-white">
          Back to the lobby
        </Link>
      </div>
    );
  }

  const closing = closesIn(room.closes_at);
  const closed = closing === "closed";
  const short = room.entry_fee - (balance ?? 0); // coins missing to afford the buy-in
  const shares = payoutShares(room.member_count);

  return (
    // Same frame as the fighter profile: one wide container, a main column and
    // a 320px rail side by side from lg, stacked below.
    <div className="mx-auto w-full max-w-6xl px-3 py-8 text-left sm:px-4">
      <Link to="/rooms" className="text-sm text-zinc-500 transition-colors hover:text-white">
        Lobby
      </Link>

      {/* ---- hero: the cover IS the header. Name and owner sit on the image
          over a bottom fade, so a photo cover gets the whole stage. ---- */}
      <header className="relative mt-3 overflow-hidden rounded-lg border border-zinc-700">
        <RoomCover seed={room.id} src={room.cover_url} className="block h-52 w-full sm:h-64" />
        {/* fade so white text stays readable on any photo, bright or not */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"
        />

        <div className="absolute inset-x-0 bottom-0 p-4 sm:p-5">
          <div className="border-l-2 border-[#d33a2c] pl-3">
            <div className="text-[9px] font-medium uppercase tracking-[0.2em] text-zinc-400">
              {room.is_public ? "Public room" : "Private room"}
            </div>
            {/* size/spacing INLINE: index.css's unlayered `h1` rule (48px,
                32px margins) beats Tailwind classes; inline styles beat it */}
            <h1
              className="break-words uppercase leading-relaxed text-white"
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "clamp(1rem, 2.4vw, 1.25rem)",
                letterSpacing: 0,
                margin: "6px 0 0",
              }}
            >
              {room.name}
            </h1>
            <div
              className="mt-1 text-sm italic text-zinc-300"
              style={{ fontFamily: "var(--font-rundown)" }}
            >
              by{" "}
              <Link
                to={`/users/${room.owner_id}`}
                className="text-white underline-offset-2 hover:text-[#e8503f] hover:underline"
              >
                {room.owner_name}
              </Link>
            </div>
          </div>
        </div>

        {/* top-right corner: owner gets the cover picker (a <label> around a
            hidden input, so the whole chip opens it); everyone else can report
            a photo — there's nothing to report on generated art. Flat chips. */}
        {room.is_owner && (
          // Just a dot, after the one on the career-phase cards: no words on
          // the photo. Bigger and fully opaque so it holds up on any cover; on
          // hover it picks up the phases' "open" ring in the app red, and it
          // pulses red while uploading. The label's padding is the hit area —
          // the dot alone would be too small a target. Name via title + sr-only.
          <label
            title={room.cover_url ? "Change cover" : "Add cover"}
            className="group/cover absolute right-1.5 top-1.5 cursor-pointer p-2"
          >
            <span
              aria-hidden
              className={`block h-2.5 w-2.5 rounded-full transition-all duration-200 group-hover/cover:bg-[#d33a2c] group-hover/cover:shadow-[0_0_0_4px_#d33a2c40] ${
                coverBusy ? "animate-pulse bg-[#d33a2c]" : "bg-white"
              }`}
            />
            <span className="sr-only">
              {coverBusy ? "Uploading cover" : room.cover_url ? "Change cover" : "Add cover"}
            </span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={coverBusy}
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = ""; // so picking the same file again still fires
                if (f) handleCover(f);
              }}
            />
          </label>
        )}
        {!room.is_owner && room.cover_url && (
          <button
            type="button"
            onClick={handleReport}
            disabled={room.has_reported_cover}
            className="absolute right-3 top-3 rounded-md bg-black/60 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.15em] text-zinc-400 transition-colors hover:text-[#e8503f] disabled:cursor-default disabled:hover:text-zinc-400"
          >
            {room.has_reported_cover ? "Reported" : "Report cover"}
          </button>
        )}
      </header>
      {coverMsg && <div className="mt-2 text-xs text-zinc-400">{coverMsg}</div>}

      <section className="mt-5 flex flex-col gap-5 sm:mt-6 sm:gap-6 lg:flex-row lg:items-start">
        {/* ---- rail: the pot and the one action. First in the DOM so it sits
            right under the hero on phones; lg:order-last moves it to the right
            on desktop, where the eye reaches it after the board. ---- */}
        <aside className="flex flex-col gap-5 sm:gap-6 lg:order-last lg:w-80 lg:shrink-0">
          <div className={CARD}>
            <CardLabel>Pot</CardLabel>
            <div className="mt-3 flex items-center gap-3">
              <CoinIcon size={28} className="shrink-0" />
              <span
                style={{ fontFamily: "var(--font-display)" }}
                className="text-3xl tabular-nums text-[#ffd75e]"
              >
                {room.pot.toLocaleString()}
              </span>
            </div>
            {/* red rule + rundown italic, same block as "You're in". A <div>
                carries the margin: index.css's unlayered `p { margin: 0 }`
                silently eats mt-* on a <p>. */}
            <div
              className="mt-3 border-l-2 border-[#d33a2c] pl-3 text-xs italic leading-snug text-zinc-400"
              style={{ fontFamily: "var(--font-rundown)" }}
            >
              {room.member_count < 3
                ? "Winner takes all , but the split opens up to 60 / 30 / 10 once 3 players are in."
                : "Split 60 / 30 / 10 between the top three when the room closes."}
            </div>

            {/* facts as a hairline list, label left / value right */}
            <dl className="mt-4 divide-y divide-zinc-800 border-t border-zinc-800 text-sm">
              {[
                {
                  k: "Entry",
                  v: room.entry_fee === 0 ? "Free" : (
                    <span className="flex items-center gap-1.5 text-[#ffd75e]">
                      <CoinIcon size={12} />
                      {room.entry_fee.toLocaleString()}
                    </span>
                  ),
                },
                { k: "Players", v: room.member_count },
                { k: "Closes", v: closed ? "Closed" : `in ${closing}` },
              ].map((row) => (
                <div key={row.k} className="flex items-center justify-between py-2.5">
                  <dt className="text-zinc-500">{row.k}</dt>
                  <dd className="tabular-nums text-zinc-200">{row.v}</dd>
                </div>
              ))}
            </dl>

            {/* the one thing to do on this page */}
            <div className="mt-4">
              {room.is_member ? (
                <div className="border-l-2 border-[#d33a2c] pl-3">
                  <div className="text-sm font-semibold text-white">You're in</div>
                  <div
                    className="mt-0.5 text-xs italic text-zinc-400"
                    style={{ fontFamily: "var(--font-rundown)" }}
                  >
                    Picks you make from here on count toward this room.
                  </div>
                </div>
              ) : closed ? (
                <p className="text-sm text-zinc-500">This room is closed, no new entries.</p>
              ) : (
                <>
                  {/* solid flat red, like the profile's primary action — no sheen */}
                  <button
                    onClick={handleJoin}
                    disabled={joining || short > 0}
                    className="w-full rounded-lg bg-[#d33a2c] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wide text-white transition-colors hover:bg-[#e8503f] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[#d33a2c]"
                  >
                    {joining
                      ? "Joining…"
                      : room.entry_fee === 0
                        ? "Join for free"
                        : `Join for ${room.entry_fee.toLocaleString()} coins`}
                  </button>
                  {balance !== null && (
                    <div
                      className="mt-3 flex flex-wrap items-center gap-1 border-l-2 border-[#d33a2c] pl-3 text-xs italic text-zinc-400"
                      style={{ fontFamily: "var(--font-rundown)" }}
                    >
                      You have <CoinIcon size={11} />
                      <span className="not-italic tabular-nums text-[#ffd75e]">{balance.toLocaleString()}</span>
                      {short > 0 && (
                        <>
                          <span>— {short.toLocaleString()} short.</span>
                          <Link to="/coins" className="text-[#d33a2c] underline underline-offset-2">
                            Get coins
                          </Link>
                        </>
                      )}
                    </div>
                  )}
                </>
              )}
              {joinError && <p className="error text-sm">{joinError}</p>}
            </div>
          </div>
        </aside>

        {/* ---- main column: the standings (members) or who's playing ---- */}
        <div className="flex min-w-0 flex-1 flex-col gap-5 sm:gap-6">
          <div className={CARD}>
            <div className="mb-3 flex items-baseline justify-between gap-3">
              <CardLabel>{room.is_member ? "Leaderboard" : "Players"}</CardLabel>
              <span className="text-[10px] tabular-nums text-zinc-500">
                {room.member_count} {room.member_count === 1 ? "player" : "players"}
              </span>
            </div>

            {room.is_member && board ? (
              board.length === 0 ? (
                <p className="py-6 text-center text-sm text-zinc-500">
                  No settled picks yet,the board fills in as fights get results.
                </p>
              ) : (
                <ol className="divide-y divide-zinc-800">
                  {board.map((row, i) => {
                    const paid = i < shares.length;
                    return (
                      <li key={row.id} className="flex items-center gap-3 py-2.5">
                        {/* the paid places carry the red rule, the rest don't */}
                        <span
                          className={`w-7 shrink-0 border-l-2 pl-2 text-xs tabular-nums ${
                            paid ? "border-[#d33a2c] text-white" : "border-transparent text-zinc-500"
                          }`}
                          style={{ fontFamily: "var(--font-display)" }}
                        >
                          {i + 1}
                        </span>
                        <Avatar url={row.avatar_url} name={row.name} size={28} />
                        <Link
                          to={`/users/${row.id}`}
                          className="min-w-0 flex-1 truncate text-sm text-zinc-200 underline-offset-2 hover:text-white hover:underline"
                        >
                          {row.name}
                        </Link>
                        {paid && (
                          <span className="shrink-0 text-[10px] font-medium uppercase tracking-[0.15em] text-[#ffd75e]">
                            {shares[i]}
                          </span>
                        )}
                        <span className="w-12 shrink-0 text-right text-xs tabular-nums text-zinc-500">
                          {row.correct}/{row.settled}
                        </span>
                        <span className="w-16 shrink-0 text-right text-sm font-semibold tabular-nums text-white">
                          {row.points}
                          <span className="ml-1 text-[10px] font-normal text-zinc-500">pts</span>
                        </span>
                      </li>
                    );
                  })}
                </ol>
              )
            ) : room.members.length === 0 ? (
              <p className="py-6 text-center text-sm text-zinc-500">
                Nobody has joined yet, be the first bro!.
              </p>
            ) : (
              <>
                <ul className="divide-y divide-zinc-800">
                  {room.members.map((m) => (
                    <li key={m.id}>
                      <Link
                        to={`/users/${m.id}`}
                        className="flex items-center gap-3 py-2.5 text-sm text-zinc-200 transition-colors hover:text-white"
                      >
                        <Avatar url={m.avatar_url} name={m.name} size={28} />
                        <span className="truncate">{m.name}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 text-[11px] text-zinc-500">
                  Join the room to see its leaderboard.
                </div>
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
