import { type NextConsensus } from "../api";
import { Avatar } from "./Avatar";

//homepage widget
export function PunditConsensus({ data }: { data: NextConsensus | null }) {
  // hide entirely if there's no upcoming card or we couldn't match the main event
  if (!data || !data.event || !data.fight || !data.consensus) return null;

  const { event, fight, consensus } = data;
  const { a_pct, b_pct, voted, roster, lean, voters } = consensus;
  const leansA = lean === fight.fighter_a;
  const leansB = lean === fight.fighter_b;

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 sm:p-6">
      {/* header */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#d33a2c]">
            Pundit consensus
          </p>
          <h2 className="truncate text-sm font-semibold text-white">{event.title}</h2>
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
            <p className={`truncate text-sm font-semibold ${leansA ? "text-white" : "text-zinc-400"}`}>
              {fight.fighter_a}
            </p>
            {fight.odds_a && <p className="text-xs text-zinc-500">{fight.odds_a}</p>}
          </div>
        </div>

        <span className="shrink-0 text-xs font-bold text-zinc-600">VS</span>

        {/* B */}
        <div className="flex min-w-0 flex-1 items-center justify-end gap-2 text-right">
          <div className="min-w-0">
            <p className={`truncate text-sm font-semibold ${leansB ? "text-white" : "text-zinc-400"}`}>
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

      {/* footer: n-of-m + voter avatars */}
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="text-xs text-zinc-500">
          {voted} of {roster} pundit{roster === 1 ? "" : "s"} in
        </span>
        {voters.length > 0 && (
          <div className="flex -space-x-2">
            {voters.slice(0, 6).map((v) => (
              <div
                key={v.username}
                title={`${v.username} → ${v.picked}`}
                className="rounded-full ring-2 ring-zinc-900"
              >
                <Avatar url={v.avatar_url} name={v.username} size={22} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
