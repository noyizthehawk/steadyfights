import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthError, createRoom } from "../api";
import { errorMessage } from "../lib/errorMessage";

/** "yyyy-MM-ddTHH:mm" in LOCAL time — the format <input type="datetime-local"> wants.
 *  (Can't use toISOString() here: that's UTC and would shift the min by the timezone offset.) */
function toLocalInputValue(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export default function CreateRoomPage() {
  const [name, setName] = useState("");
  const [fee, setFee] = useState("0");
  const [closesAt, setClosesAt] = useState("");
  const [isPublic, setIsPublic] = useState(false); // private by default, like the backend
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  // earliest allowed close time: an hour from now (no point in a room that closes instantly)
  const minCloses = toLocalInputValue(new Date(Date.now() + 60 * 60 * 1000));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // mirror the backend's checks so most mistakes never leave the browser
    if (!name.trim()) return setError("Give your room a name");
    const entryFee = Number(fee || 0);
    if (!Number.isInteger(entryFee) || entryFee < 0)
      return setError("Entry fee must be a whole number of coins");
    if (!closesAt) return setError("Pick when the room closes");
    const closes = new Date(closesAt); // datetime-local parses as LOCAL time
    if (closes.getTime() <= Date.now()) return setError("Close time must be in the future");

    setSubmitting(true);
    try {
      await createRoom({
        name: name.trim(),
        entry_fee: entryFee,
        // toISOString() converts the local pick to UTC ("...Z"), which the
        // backend normalizes and stores — keeps every clock in the app on UTC
        closes_at: closes.toISOString(),
        is_public: isPublic,
      });
      navigate("/rooms");
    } catch (err) {
      if (err instanceof AuthError) return navigate("/login");
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="mx-auto max-w-lg">
        <Link to="/rooms" className="text-sm text-zinc-400 hover:text-white">
          ← Back to rooms
        </Link>
        <h1 className="mb-6 mt-2 text-2xl font-bold text-white">Create a Room</h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-1 block text-sm text-zinc-400">Room name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Saturday Night Fights"
              maxLength={60}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-white placeholder-zinc-500 focus:border-red-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-zinc-400">
              Entry fee <span className="text-[#ffd75e]">(coins — 0 = free room)</span>
            </label>
            <input
              type="number"
              min={0}
              step={1}
              value={fee}
              onChange={(e) => setFee(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-white focus:border-red-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-zinc-400">
              Closes at <span className="text-zinc-500">(when the winners get paid)</span>
            </label>
            <input
              type="datetime-local"
              min={minCloses}
              value={closesAt}
              onChange={(e) => setClosesAt(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-white focus:border-red-500 focus:outline-none"
            />
          </div>

          {/* visibility — two big selectable cards instead of a bare checkbox */}
          <div>
            <label className="mb-1 block text-sm text-zinc-400">Visibility</label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { v: false, label: "Private", desc: "Only your friends can see it" },
                { v: true, label: "Public", desc: "Anyone can find and join" },
              ].map((o) => (
                <button
                  type="button"
                  key={o.label}
                  onClick={() => setIsPublic(o.v)}
                  className={`rounded-xl border p-4 text-left transition-colors ${
                    isPublic === o.v
                      ? "border-red-500 bg-red-500/10"
                      : "border-zinc-700 hover:border-zinc-500"
                  }`}
                >
                  <div className="font-semibold text-white">{o.label}</div>
                  <div className="mt-1 text-xs text-zinc-400">{o.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {error && <p className="error">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-red-600 px-4 py-2.5 font-semibold text-white transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create Room"}
          </button>
        </form>
      </div>
    </div>
  );
}
