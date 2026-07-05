import type { Room } from "../api";
import { CoinIcon } from "./CoinIcon";
import { RoomCover } from "./RoomCover";
import { closesIn } from "../lib/rooms";

/** One full-width room row in the lobby, styled like an arcade menu entry:
 *  cover | ▶ name | ENTRY readout | CLOSES IN readout | badge + JOIN cue.
 *  The fixed sm: column widths are what keep readouts vertically aligned
 *  across rows — the "high-score table" look. On mobile the readout columns
 *  hide and compact stats render inline under the name instead. */
export function RoomCard({ room }: { room: Room }) {
  const closing = closesIn(room.closes_at);
  const closed = closing === "closed";

  const badge = (
    <span
      className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] tracking-widest ${
        room.is_public
          ? "border-orange-500/60 text-orange-400"
          : "border-zinc-600 text-zinc-400"
      }`}
    >
      {room.is_public ? "PUBLIC" : "PRIVATE"}
    </span>
  );

  const fee = (
    <span className="flex items-center gap-1.5 text-[#ffd75e]">
      <CoinIcon size={12} className="shrink-0" />
      <span style={{ fontFamily: "var(--font-display)" }} className="text-[10px]">
        {room.entry_fee === 0 ? "FREE" : room.entry_fee.toLocaleString()}
      </span>
    </span>
  );

  return (
    <article className="group grid grid-cols-[auto_minmax(0,1fr)] items-center overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900 transition-colors hover:border-red-500/60 sm:grid-cols-[auto_minmax(0,1fr)_6.5rem_6.5rem_7rem] lg:grid-cols-[auto_minmax(0,1fr)_9.5rem_10.5rem_11rem]">
      {/* aspect-[5/3] matches the svg's 160x96 viewBox exactly, so no pixel
          cells get cropped at the cover edges */}
      <RoomCover seed={room.id} className="aspect-[5/3] h-20 shrink-0" />

      {/* name column — the only flexible one; ▶ cursor keeps its slot so the
          name never shifts, only fades/blinks in on hover */}
      <div className="min-w-0 px-4 py-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="cursor-blink w-3 shrink-0 text-red-500 opacity-0"
            style={{ fontFamily: "var(--font-display)", fontSize: 10 }}
          >
            ▶
          </span>
          <h3 className="truncate uppercase font-display text-white">{room.name}</h3>
          <span className="sm:hidden">{badge}</span>
        </div>
        {/* compact stats (phones only) — from sm: up the readout columns take
            over: label-less at sm, full labels at lg */}
        <div className="mt-1.5 flex items-center gap-4 pl-5 text-xs sm:hidden">
          {fee}
          <span className={closed ? "text-zinc-500" : "text-zinc-400"}>
            {closed ? "closed" : `closes in ${closing}`}
          </span>
        </div>
      </div>

      {/* single-line readouts: tiny label INLINE before each value so the whole
          row reads as one horizontal score-table line */}
      <div className="hidden items-center gap-2 px-2 sm:flex">
        <span className="hidden text-[9px] tracking-widest text-zinc-400 lg:inline">ENTRY</span>
        {fee}
      </div>

      <div className="hidden items-center gap-2 px-2 sm:flex">
        <span className="hidden text-[9px] tracking-widest text-zinc-400 lg:inline">CLOSES</span>
        <span
          style={{ fontFamily: "var(--font-display)" }}
          className={`text-[10px] ${closed ? "text-zinc-500" : "text-zinc-300"}`}
        >
          {closed ? "CLOSED" : closing.toUpperCase()}
        </span>
      </div>

      <div className="hidden items-center justify-end gap-3 px-4 sm:flex">
        {badge}
        <span
          style={{ fontFamily: "var(--font-display)" }}
          className="hidden text-[9px] text-zinc-500 transition-colors group-hover:text-red-500 lg:inline"
        >
          JOIN ▸
        </span>
      </div>
    </article>
  );
}
