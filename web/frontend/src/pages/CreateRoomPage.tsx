import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthError, createRoom, uploadRoomCover } from "../api";
import { RoomCover } from "../components/RoomCover";
import { errorMessage } from "../lib/errorMessage";

const MAX_COVER_MB = 10; // mirrors MAX_COVER_BYTES on the backend

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
  const [cover, setCover] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const navigate = useNavigate();

  // local blob URL so the picked photo previews before anything is uploaded;
  // revoked on change/unmount or every pick would leak the file in memory
  useEffect(() => {
    if (!cover) return setPreview(null);
    const url = URL.createObjectURL(cover);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [cover]);

  function pickCover(f: File | undefined) {
    setError("");
    if (!f) return;
    if (f.size > MAX_COVER_MB * 1024 * 1024)
      return setError(`Cover must be ${MAX_COVER_MB} MB or smaller`);
    setCover(f);
  }

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
      const room = await createRoom({
        name: name.trim(),
        entry_fee: entryFee,
        // toISOString() converts the local pick to UTC ("...Z"), which the
        // backend normalizes and stores — keeps every clock in the app on UTC
        closes_at: closes.toISOString(),
        is_public: isPublic,
      });
      // the cover is a second request on purpose: the room already exists, so
      // a failed upload can't lose it. On failure, send the owner to the room
      // page, where the banner has a retry button.
      if (cover) {
        try {
          await uploadRoomCover(room.id, cover);
        } catch (err) {
          if (err instanceof AuthError) return navigate("/login");
          return navigate(`/rooms/${room.id}`, {
            state: { coverError: `Room created, but the cover didn't upload: ${errorMessage(err)}` },
          });
        }
      }
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

          {/* cover — optional, but sitting right in the form so people actually
              add one. Shows the generated art until a photo is picked, so the
              owner sees exactly what the lobby tile will look like either way. */}
          <div>
            <label className="mb-1 block text-sm text-zinc-400">
              Cover photo <span className="text-zinc-500">(optional — shows on your lobby tile)</span>
            </label>
            <div className="flex items-center gap-4">
              <RoomCover
                seed={1}
                src={preview}
                className="aspect-[5/3] h-20 shrink-0 rounded-lg border border-zinc-700"
              />
              <div className="flex flex-col items-start gap-1.5">
                <label className="cursor-pointer rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 transition-colors hover:border-zinc-500">
                  {cover ? "Choose a different photo" : "Upload a photo"}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={(e) => {
                      pickCover(e.target.files?.[0]);
                      e.target.value = ""; // so re-picking the same file still fires
                    }}
                  />
                </label>
                {cover && (
                  <button
                    type="button"
                    onClick={() => setCover(null)}
                    className="text-xs text-zinc-500 hover:text-zinc-300"
                  >
                    Remove
                  </button>
                )}
              </div>
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
