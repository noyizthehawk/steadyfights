import { Link } from "react-router-dom";
import { NotableUser } from "../api";
import { Avatar } from "./Avatar";

// Curated showcase of notable users (e.g. MMA YouTubers) with their overall
// pick accuracy. Each row links to that user's past events.
export function NotableUsers({ users }: { users: NotableUser[] }) {
  if (users.length === 0) return null;

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        pundit picks
      </h2>
      <ul className="space-y-2">
        {users.map((u) => (
          <li key={u.id}>
            <Link
              to={`/users/${u.id}/events`}
              className="flex items-center gap-3 rounded-lg border border-zinc-800 p-2.5 transition-colors hover:bg-zinc-800"
            >
              <Avatar url={u.avatar_url} name={u.username} size={36} />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-1.5 truncate text-sm font-semibold text-white">
                  <span className="truncate">{u.username}</span>
                  {u.have_youtube && (
                    <span className="shrink-0 rounded bg-[#d33a2c] px-1 py-0.5 text-[9px] font-bold leading-none text-white">
                      YT
                    </span>
                  )}
                </p>
                <p className="text-xs text-zinc-500">
                  {u.fights_settled > 0 ? `${u.fights_settled} settled` : "no picks yet"}
                </p>
              </div>
              <span className="shrink-0 font-bold tabular-nums text-[#d33a2c]">
                {u.winrate != null ? `${u.winrate}%` : "—"}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
