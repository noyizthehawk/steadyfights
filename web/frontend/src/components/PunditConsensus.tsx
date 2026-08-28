import { useState } from "react";
import { type NextConsensus } from "../api";
import { Avatar } from "./Avatar";

//homepage widget
export function PunditConsensus({ data }: { data: NextConsensus | null }) {
  // expandable "who picked who" breakdown, collapsed by default
  const [open, setOpen] = useState(false);

  // hide entirely if there's no upcoming card or we couldn't match the main event
  if (!data || !data.event || !data.fight || !data.consensus) return null;

  const { event, fight, consensus } = data;
  const { a_pct, b_pct, voted, roster, lean, voters } = consensus;
  const leansA = lean === fight.fighter_a;
  const leansB = lean === fight.fighter_b;

  // split the voters by the corner they picked, so the breakdown can mirror the
  // fighters row above: A-pickers on the left, B-pickers on the right.
  const aVoters = voters.filter((v) => v.picked === fight.fighter_a);
  const bVoters = voters.filter((v) => v.picked === fight.fighter_b);

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 sm:p-6">
      {/* header */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#d33a2c]">
            Pundit consensus for next main event
          </p>
          <h2 className="break-words text-sm font-semibold text-white">{event.title}</h2>
        </div>
        <span className="shrink-0 text-xs text-zinc-500">
          {new Date(event.date * 1000).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })}
        </span>
      </div>

      {/* fighters */}
      <div className="mb-4 flex items-center justify-between gap-3">
        {/* A */}
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {fight.img_a && (
            <img
              src={fight.img_a}
              alt={fight.fighter_a}
              className="h-14 w-14 shrink-0 rounded-full object-cover object-top"
            />
          )}
          <div className="min-w-0">
            <p className={`break-words text-sm font-semibold ${leansA ? "text-white" : "text-zinc-400"}`}>
              {fight.fighter_a}
            </p>
            {fight.odds_a && <p className="text-xs text-zinc-500">{fight.odds_a}</p>}
          </div>
        </div>

        <span className="shrink-0 text-xs font-bold text-zinc-600">VS</span>

        {/* B */}
        <div className="flex min-w-0 flex-1 items-center justify-end gap-2 text-right">
          <div className="min-w-0">
            <p className={`break-words text-sm font-semibold ${leansB ? "text-white" : "text-zinc-400"}`}>
              {fight.fighter_b}
            </p>
            {fight.odds_b && <p className="text-xs text-zinc-500">{fight.odds_b}</p>}
          </div>
          {fight.img_b && (
            <img
              src={fight.img_b}
              alt={fight.fighter_b}
              className="h-14 w-14 shrink-0 rounded-full object-cover object-top"
            />
          )}
        </div>
      </div>

      {/* split bar, or "picks coming in" before anyone's posted */}
      {voted > 0 ? (
        <>
          <div className="mb-1.5 flex items-center justify-between text-xs font-bold text-white">
            <span>{a_pct}%</span>
            <span>{b_pct}%</span>
          </div>
          <div className="flex h-2.5 overflow-hidden rounded-full bg-zinc-800">
            <div style={{ width: `${a_pct}%` }} className={leansA ? "bg-[#d33a2c]" : "bg-zinc-600"} />
            <div style={{ width: `${b_pct}%` }} className={leansB ? "bg-[#d33a2c]" : "bg-zinc-600"} />
          </div>
        </>
      ) : (
        <div className="rounded-full bg-zinc-800 px-3 py-2 text-center text-xs text-zinc-500">
          Picks coming in…
        </div>
      )}

      {/* footer: n-of-m + a collapsed avatar preview; the whole row toggles the
          full "who picked who" breakdown when there are voters. */}
      {voters.length > 0 ? (
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="mt-3 flex w-full items-center justify-between gap-2 rounded-lg px-1 py-1 text-left transition-colors hover:bg-zinc-800/60"
        >
          <span className="text-xs text-zinc-500">
            {voted} of {roster} pundit{roster === 1 ? "" : "s"} in
          </span>
          <span className="flex items-center gap-2">
            {/* collapsed preview stack, hidden once expanded */}
            {!open && (
              <span className="flex -space-x-2">
                {voters.slice(0, 6).map((v) => (
                  <span key={v.username} className="rounded-full ring-2 ring-zinc-900">
                    <Avatar url={v.avatar_url} name={v.username} size={22} />
                  </span>
                ))}
              </span>
            )}
            <svg
              viewBox="0 0 20 20"
              className={`h-4 w-4 shrink-0 text-zinc-500 transition-transform ${open ? "rotate-180" : ""}`}
              fill="currentColor"
              aria-hidden="true"
            >
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </span>
        </button>
      ) : (
        <div className="mt-3 text-xs text-zinc-500">
          {voted} of {roster} pundit{roster === 1 ? "" : "s"} in
        </div>
      )}

      {/* expanded breakdown: A-pickers (left) vs B-pickers (right) */}
      {open && voters.length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-zinc-800 pt-3">
          <div className="min-w-0 space-y-2">
            {aVoters.length === 0 ? (
              <p className="text-xs text-zinc-600">—</p>
            ) : (
              aVoters.map((v) => (
                <div key={v.username} className="flex min-w-0 items-center gap-2">
                  <Avatar url={v.avatar_url} name={v.username} size={20} />
                  <span className="truncate text-xs text-zinc-300">{v.username}</span>
                </div>
              ))
            )}
          </div>
          <div className="min-w-0 space-y-2">
            {bVoters.length === 0 ? (
              <p className="text-right text-xs text-zinc-600">—</p>
            ) : (
              bVoters.map((v) => (
                <div key={v.username} className="flex min-w-0 items-center justify-end gap-2 text-right">
                  <span className="truncate text-xs text-zinc-300">{v.username}</span>
                  <Avatar url={v.avatar_url} name={v.username} size={20} />
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
