import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import {
  getFriends,
  getPending,
  acceptInvite,
  declineInvite,
  inviteFriend,
  type Friend,
  type PendingInvite,
} from "../api";

export default function FriendsPage() {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [pending, setPending] = useState<PendingInvite[]>([]);
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");

  // reload both lists (called on mount and after any action)
  async function load() {
    setFriends(await getFriends());
    setPending(await getPending());
  }
  useEffect(() => {
    load();
  }, []);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await inviteFriend({ email });
      setEmail("");
      setMsg("Invite sent ✓");
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Could not send invite");
    }
  }

  async function handleAccept(id: number) {
    await acceptInvite(id);
    load();
  }
  async function handleDecline(id: number) {
    await declineInvite(id);
    load();
  }

  return (
    <div className="page">
      <h1 className="mb-4 text-2xl font-bold text-white">Friends</h1>

      {/* invite by email */}
      <form onSubmit={handleInvite} className="mb-6 flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Friend's email"
          className="flex-1 rounded bg-zinc-800 px-3 py-2 text-white"
        />
        <button className="rounded bg-[#d33a2c] px-4 py-2 font-semibold text-white">
          Invite
        </button>
      </form>
      {msg && <p className="mb-4 text-sm text-zinc-400">{msg}</p>}

      {/* two containers: friends, and invites waiting on you. Side by side
          from sm up, stacked on phones. */}
      <div className="grid gap-5 sm:grid-cols-2">
        <section className="rounded-xl border border-zinc-800 p-4">
          <ContainerHeading title="Friends" count={friends.length} />
          {friends.length === 0 ? (
            <Empty>No friends yet, invite one above.</Empty>
          ) : (
            <ul className="space-y-1">
              {friends.map((f) => (
                <li key={f.id}>
                  <Link
                    to={`/users/${f.id}`}
                    className="flex items-center gap-3 rounded-lg p-2 text-sm text-zinc-200 hover:bg-zinc-800/60 hover:text-white"
                  >
                    <Avatar url={null} name={f.username} size={28} />
                    <span className="truncate">{f.username}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* red frame only while something is waiting on you */}
        <section
          className={
            pending.length > 0
              ? "rounded-xl border border-[#d33a2c]/70 p-4"
              : "rounded-xl border border-zinc-800 p-4"
          }
        >
          <ContainerHeading title="Pending invites" count={pending.length} />
          {pending.length === 0 ? (
            <Empty>No pending invites.</Empty>
          ) : (
            <ul className="space-y-1">
              {pending.map((p) => (
                <li key={p.invite_id} className="flex items-center justify-between gap-3 p-2">
                  <span className="flex min-w-0 items-center gap-3 text-sm text-zinc-200">
                    <Avatar url={null} name={p.from} size={28} />
                    <span className="truncate">{p.from}</span>
                  </span>
                  {/* flat, no gloss: accept is the filled one, decline stays quiet */}
                  <div className="flex shrink-0 gap-2">
                    <button
                      onClick={() => handleAccept(p.invite_id)}
                      className="cursor-pointer rounded-md bg-[#d33a2c] px-3 py-1 text-xs font-semibold text-white hover:bg-[#e8503f]"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => handleDecline(p.invite_id)}
                      className="cursor-pointer rounded-md border border-zinc-700 px-3 py-1 text-xs text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
                    >
                      Decline
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

/** P2 heading hung off the red rule, with the count beside it. An <h3>:
 *  index.css styles h1/h2 outside any @layer, which would override these. */
function ContainerHeading({ title, count }: { title: string; count: number }) {
  return (
    <div className="mb-4 flex items-baseline gap-3 border-l-2 border-[#d33a2c] pl-3">
      <h3 className="m-0 text-[11px] uppercase leading-relaxed text-white" style={{ fontFamily: "var(--font-display)" }}>
        {title}
      </h3>
      <span className="text-xs italic tabular-nums text-zinc-500" style={{ fontFamily: "var(--font-rundown)" }}>
        {count}
      </span>
    </div>
  );
}

/** Empty-state line. A <div>: index.css's unlayered `p { margin: 0 }` would
 *  eat spacing on a <p>. */
function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-2 py-1 text-sm italic text-zinc-500" style={{ fontFamily: "var(--font-rundown)" }}>
      {children}
    </div>
  );
}
