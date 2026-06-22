import { useEffect, useState } from "react";
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

      {/* pending invites */}
      <h2 className="mb-2 text-lg font-semibold text-white">Pending invites</h2>
      {pending.length === 0 ? (
        <p className="mb-6 text-sm text-zinc-500">No pending invites.</p>
      ) : (
        <ul className="mb-6 space-y-2">
          {pending.map((p) => (
            <li
              key={p.invite_id}
              className="flex items-center justify-between rounded-lg bg-zinc-800 p-3 text-white"
            >
              <span>{p.from}</span>
              <div className="flex gap-2">
                <button
                  onClick={() => handleAccept(p.invite_id)}
                  className="rounded bg-green-600 px-3 py-1 text-sm"
                >
                  Accept
                </button>
                <button
                  onClick={() => handleDecline(p.invite_id)}
                  className="rounded bg-zinc-600 px-3 py-1 text-sm"
                >
                  Decline
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* accepted friends */}
      <h2 className="mb-2 text-lg font-semibold text-white">My friends</h2>
      {friends.length === 0 ? (
        <p className="text-sm text-zinc-500">No friends yet.</p>
      ) : (
        <ul className="space-y-2">
          {friends.map((f) => (
            <li key={f.id} className="rounded-lg bg-zinc-800 p-3 text-white">
              {f.email}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
