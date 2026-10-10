import { Link } from "react-router-dom";
import type { Room } from "../api";
import { RoomCover } from "./RoomCover";

/** One room in the lobby, in the same language as the homepage event tiles
 *  (EventTileMini): the picture does the talking, with just the name, owner
 *  and player count underneath. Fee, close time and visibility live on the
 *  room page — the tab already says public vs private. */
export function RoomCard({ room }: { room: Room }) {
  return (
    <article className="group text-left">
      {/* picture and name each link to the room; the owner name links to
          their profile. Separate links, because an <a> can't nest in an <a>.
          (An invisible full-tile overlay link was tried first — the positioned
          image box painted over it and swallowed every click.) */}
      <Link to={`/rooms/${room.id}`} className="block">
        <div className="aspect-[4/3] w-full overflow-hidden rounded-xl shadow-lg transition-transform duration-200 group-hover:scale-105">
          <RoomCover seed={room.id} src={room.cover_url} className="block h-full w-full" />
        </div>
      </Link>

      {/* caption hangs off the rundown's hairline red rule (FighterBio), with
          mt-4 for a clear gap: the picture grows 5% on hover. On a <div>, so
          index.css's unlayered `p { margin: 0 }` can't eat the margin. */}
      <div className="mt-4 border-l-2 border-[#d33a2c] pl-3">
        <Link
          to={`/rooms/${room.id}`}
          // pixel faces need air: leading-relaxed instead of tight, and long
          // names wrap to a second line instead of being cut off mid-word
          className="line-clamp-2 break-words text-[10px] leading-relaxed text-zinc-300 hover:text-white"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {room.name}
        </Link>

        {/* the rundown's italic face, so the room's own name is the only
            pixel-font text on the tile. One fact per line. */}
        <div
          className="mt-2 space-y-0.5 text-xs italic text-zinc-500"
          style={{ fontFamily: "var(--font-rundown)" }}
        >
          <div className="flex items-center gap-1">
            <span>by</span>
            <Link
              to={`/users/${room.owner_id}`}
              className="truncate text-zinc-400 underline-offset-2 hover:text-red-400 hover:underline"
            >
              {room.owner_name}
            </Link>
          </div>
          <div>
            {room.member_count} {room.member_count === 1 ? "player" : "players"}
          </div>
        </div>
      </div>
    </article>
  );
}
