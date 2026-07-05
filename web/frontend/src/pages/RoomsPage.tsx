import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AuthError,
  getBalance,
  getMyRooms,
  getPrivateRooms,
  getPublicRooms,
  type Room,
} from "../api";
import { CoinIcon } from "../components/CoinIcon";
import { RoomCard } from "../components/RoomCard";
import { errorMessage } from "../lib/errorMessage";
import "../rooms.css";

type Tab = "public" | "private" | "mine";

export default function RoomsPage() {
  const [tab, setTab] = useState<Tab>("public");
  const [q, setQ] = useState(""); // what's in the input right now
  const [debouncedQ, setDebouncedQ] = useState(""); // what we actually search with
  const [page, setPage] = useState(1);

  const [rooms, setRooms] = useState<Room[]>([]);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  // Debounce the search: only fire a request 300ms after typing stops,
  // and always jump back to page 1 for a new query.
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedQ(q);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  // Gold balance pill (also our auth check — bounce to login if logged out)
  useEffect(() => {
    getBalance()
      .then(setBalance)
      .catch((e) => {
        if (e instanceof AuthError) navigate("/login");
      });
  }, [navigate]);

  // Fetch the current tab's rooms whenever tab / search / page changes
  useEffect(() => {
    let cancelled = false; // ignore stale responses if deps change mid-flight
    setLoading(true);
    setError("");

    (async () => {
      try {
        if (tab === "mine") {
          // my rooms is a small unpaginated list — filter it client-side
          const all = await getMyRooms();
          const filtered = debouncedQ
            ? all.filter((r) => r.name.toLowerCase().includes(debouncedQ.toLowerCase()))
            : all;
          if (!cancelled) {
            setRooms(filtered);
            setTotal(filtered.length);
            setPageSize(Math.max(filtered.length, 1));
          }
        } else {
          const data =
            tab === "public"
              ? await getPublicRooms(debouncedQ, page)
              : await getPrivateRooms(debouncedQ, page);
          if (!cancelled) {
            setRooms(data.rooms);
            setTotal(data.total);
            setPageSize(data.page_size);
          }
        }
      } catch (e) {
        if (e instanceof AuthError) return navigate("/login");
        if (!cancelled) setError(errorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [tab, debouncedQ, page, navigate]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  function emptyState() {
    if (debouncedQ) return <p className="text-zinc-400">No rooms match “{debouncedQ}”.</p>;
    if (tab === "private")
      return (
        <p className="text-zinc-400">
          Rooms your friends create show up here.{" "}
          <Link to="/friends" className="text-red-400 underline">
            Add friends
          </Link>{" "}
          to unlock the private lobby.
        </p>
      );
    if (tab === "mine")
      return <p className="text-zinc-400">You haven't joined any rooms yet — browse the public lobby.</p>;
    return <p className="text-zinc-400">No public rooms yet — create the first one!</p>;
  }

  return (
    <div className="page">
      {/* header: title + gold balance + create (create is NOT in the nav, only here) */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-white">Rooms</h1>
        <div className="ml-auto flex items-center gap-3">
          {balance !== null && (
            <span className="flex items-center gap-2 rounded-full border border-[#ffce4f66] bg-[#ffce4f14] px-3 py-1.5 text-[#ffd75e]">
              <CoinIcon size={14} className="shrink-0" />
              <span style={{ fontFamily: "var(--font-display)" }} className="text-[11px]">
                {balance.toLocaleString()}
              </span>
            </span>
          )}
          <Link
            to="/rooms/new"
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-500"
          >
            + Create Room
          </Link>
        </div>
      </div>

      {/* tabs */}
      <div className="mb-4 flex gap-2">
        {(["public", "private", "mine"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              setPage(1);
            }}
            className={`rounded-full border px-4 py-1.5 text-sm capitalize transition-colors ${
              tab === t
                ? "border-red-500/50 bg-red-500/10 text-red-400"
                : "border-transparent text-zinc-400 hover:text-white"
            }`}
          >
            {t === "mine" ? "My rooms" : t}
          </button>
        ))}
      </div>

      {/* search */}
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Search rooms by name"
        placeholder="Search rooms by name…"
        className="mb-6 w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm text-white placeholder-zinc-500 focus:border-red-500 focus:outline-none"
      />

      {error && <p className="error">{error}</p>}

      {!loading && rooms.length === 0 && !error && emptyState()}

      {/* skeleton rows while fetching — same height as a real row so the
          list doesn't jump when data lands */}
      {loading && (
        <div className="flex flex-col gap-3" aria-hidden>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl border border-zinc-800 bg-zinc-900" />
          ))}
        </div>
      )}

      {/* full-width arcade rows — key includes tab/page/query so rows re-mount
          and replay the stagger-in animation on every view change */}
      {!loading && (
        <div className="flex flex-col gap-3">
          {rooms.map((room, i) => (
            <div
              key={`${tab}:${page}:${debouncedQ}:${room.id}`}
              className="tile-in"
              style={{ animationDelay: `${Math.min(i * 40, 600)}ms` }}
            >
              <RoomCard room={room} />
            </div>
          ))}
        </div>
      )}

      {/* pager (search results and the lobby can exceed one page) */}
      {tab !== "mine" && totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-4 text-sm">
          <button
            onClick={() => setPage((p) => p - 1)}
            disabled={page <= 1}
            className="rounded-lg border border-red-500/50 px-3 py-1.5 text-red-400 transition-colors hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="text-zinc-400" style={{ fontFamily: "var(--font-display)", fontSize: 10 }}>
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="rounded-lg border border-red-500/50 px-3 py-1.5 text-red-400 transition-colors hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
