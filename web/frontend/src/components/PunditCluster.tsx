import { useState } from "react";
import type { PunditVoter } from "../api";

// Pundit picks for ONE corner of a fight.
//
// These live inside the fighter's own column, so position carries the meaning:
// a pundit shown under Silva picked Silva. No label, no "N pundits picked"
// sentence. At rest it is a single small cluster of avatars — tapping expands
// the detail. That ordering is deliberate: the reference sites for this get
// overwhelming because everything is visible at once, so nothing has priority.

function Avatar({ voter, size }: { voter: PunditVoter; size: string }) {
    const initial = voter.username.charAt(0).toUpperCase();
    return voter.avatar_url ? (
        <img
            src={voter.avatar_url}
            alt={voter.username}
            title={voter.username}
            className={`${size} shrink-0 rounded-full border border-zinc-900 object-cover`}
        />
    ) : (
        <span
            title={voter.username}
            className={`${size} flex shrink-0 items-center justify-center rounded-full border border-zinc-900 bg-zinc-700 text-[8px] font-bold text-zinc-200`}
        >
            {initial}
        </span>
    );
}

export function PunditCluster({ voters }: { voters: PunditVoter[] }) {
    const [open, setOpen] = useState(false);
    if (!voters || voters.length === 0) return null;

    return (
        <div className="mt-1.5">
            <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
                aria-label={`${voters.length} pundit${voters.length > 1 ? "s" : ""} picked this fighter`}
                // -space-x-1.5 overlaps the circles so four pundits read as one
                // object rather than a row that competes with the fighter name
                className="flex -space-x-1.5 rounded-full transition-opacity hover:opacity-80"
            >
                {voters.map((v) => (
                    <Avatar key={v.username} voter={v} size="h-5 w-5" />
                ))}
            </button>

            {open && (
                <ul className="mt-2 space-y-1.5 text-left">
                    {voters.map((v) => (
                        <li key={v.username} className="flex items-center gap-1.5">
                            <Avatar voter={v} size="h-4 w-4" />
                            <span className="truncate text-[10px] text-zinc-300">{v.username}</span>
                            {/* the pick is LLM-extracted from speech and attributed to a
                                named person — the source makes it checkable */}
                            {v.video_url && (
                                <a
                                    href={v.video_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="shrink-0 text-[10px] text-zinc-500 underline-offset-2 hover:text-blue-400 hover:underline"
                                >
                                    source
                                </a>
                            )}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}
