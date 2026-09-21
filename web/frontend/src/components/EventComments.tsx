import { useCallback, useEffect, useRef, useState } from "react";
import {
  getComments, getCommentsSince, postComment, deleteComment, voteComment,
  me, AuthError, type Comment,
} from "../api";

const POLL_MS = 8000;

/** Highest id anywhere in the tree — replies included.
 *
 * This is the polling cursor, and taking it from top-level comments alone is
 * the easy bug: a reply always has a HIGHER id than the parent it hangs under,
 * so a top-level-only max would ask the server for rows we already have, and
 * every poll would re-deliver the same replies forever.
 */
function maxId(threads: Comment[]): number {
  let max = 0;
  for (const thread of threads) {
    if (thread.id > max) max = thread.id;
    for (const reply of thread.replies ?? []) if (reply.id > max) max = reply.id;
  }
  return max;
}

function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const units: [number, string][] = [[60, "m"], [3600, "h"], [86400, "d"]];
  for (let i = units.length - 1; i >= 0; i--) {
    const [size, label] = units[i];
    if (seconds >= size) return `${Math.floor(seconds / size)}${label} ago`;
  }
  return "just now";
}

type RowProps = {
  comment: Comment;
  isReply: boolean;
  meId: number | null;
  onVote: (comment: Comment, value: 1 | -1) => void;
  onReply: (threadId: number) => void;
  onDelete: (id: number) => void;
};

/** One comment, used for both a thread root and a reply.
 *
 * Defined at module level on purpose. Nested inside EventComments it would be a
 * NEW component type on every render, so React would unmount and remount every
 * row each time a character was typed in the composer — throwing away focus and
 * any DOM state in the subtree.
 */
function Row({ comment, isReply, meId, onVote, onReply, onDelete }: RowProps) {
  const mine = !comment.deleted && comment.user?.id === meId;
  return (
    <div className={isReply ? "border-l border-zinc-800 pl-4" : ""}>
      <div className="flex items-start gap-3">
        {comment.user?.avatar_url ? (
          <img src={comment.user.avatar_url} alt=""
               className="h-8 w-8 shrink-0 rounded-full object-cover" />
        ) : (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-400">
            {comment.user?.username?.[0]?.toUpperCase() ?? "?"}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm">
            <span className="font-semibold text-white">
              {comment.user?.username ?? "[deleted]"}
            </span>
            <span className="ml-2 text-xs text-zinc-500">{timeAgo(comment.created_at)}</span>
          </p>
          <p className={`mt-0.5 text-sm break-words ${comment.deleted ? "italic text-zinc-600" : "text-zinc-300"}`}>
            {comment.deleted ? "[deleted]" : comment.body}
          </p>

          {!comment.deleted && (
            <div className="mt-1.5 flex items-center gap-4 text-xs text-zinc-500">
              <button onClick={() => onVote(comment, 1)}
                      className={`hover:text-red-400 ${comment.my_vote === 1 ? "font-semibold text-red-400" : ""}`}>
                ▲ {comment.likes}
              </button>
              <button onClick={() => onVote(comment, -1)}
                      className={`hover:text-red-400 ${comment.my_vote === -1 ? "font-semibold text-red-400" : ""}`}>
                ▼ {comment.dislikes}
              </button>
              {/* Replying to a reply targets its thread root — the same
                  flattening the server would apply, done here so the composer
                  opens in the right place. */}
              <button onClick={() => onReply(comment.parent_id ?? comment.id)}
                      className="hover:text-zinc-300">
                Reply
              </button>
              {mine && (
                <button onClick={() => onDelete(comment.id)} className="hover:text-red-400">
                  Delete
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function EventComments({ eventId }: { eventId: number }) {
  const [threads, setThreads] = useState<Comment[]>([]);
  const [meId, setMeId] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [beforeId, setBeforeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [replyDraft, setReplyDraft] = useState("");
  const [posting, setPosting] = useState(false);

  // A ref, not state: the polling interval below is created once, so it would
  // capture whatever the cursor was at mount and never see a newer value. A ref
  // is the same object every render, so the interval always reads the latest.
  const cursor = useRef(0);

  useEffect(() => {
    me().then((u) => setMeId(u.id)).catch(() => setMeId(null));
  }, []);

  // ── initial page ────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getComments(eventId)
      .then((page) => {
        if (cancelled) return;
        setThreads(page.comments);
        setHasMore(page.has_more);
        setBeforeId(page.next_before_id);
        cursor.current = maxId(page.comments);
      })
      .catch((e) => {
        if (cancelled) return;
        // Comments needing a login must not eject someone from the event page
        // they were reading — show a prompt in this section only.
        if (e instanceof AuthError) setNeedsLogin(true);
        else setError(e instanceof Error ? e.message : "Could not load comments");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [eventId]);

  /** Fold new comments into the tree, skipping any we already hold. */
  const merge = useCallback((incoming: Comment[]) => {
    setThreads((prev) => {
      // Copy the reply arrays too — mutating them in place would edit the
      // previous state object and React would not see a change.
      const next = prev.map((t) => ({ ...t, replies: [...(t.replies ?? [])] }));
      const seen = new Set<number>();
      for (const thread of next) {
        seen.add(thread.id);
        for (const reply of thread.replies) seen.add(reply.id);
      }
      for (const comment of incoming) {
        // Our own posts arrive twice: once from the POST response, once from the
        // next poll. Without this they would render as duplicates.
        if (seen.has(comment.id)) continue;
        seen.add(comment.id);
        if (comment.parent_id === null) {
          next.unshift({ ...comment, replies: [] });   // newest thread on top
        } else {
          const parent = next.find((t) => t.id === comment.parent_id);
          // A reply whose parent is on an older page we have not loaded: drop
          // it, it will arrive attached to its thread when the user pages back.
          if (parent) parent.replies.push(comment);
        }
      }
      return next;
    });
  }, []);

  // ── polling ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (needsLogin) return;
    const id = setInterval(async () => {
      // A backgrounded tab does not need fresh comments. Skipping here keeps
      // idle tabs from generating traffic all day.
      if (document.hidden) return;
      try {
        const res = await getCommentsSince(eventId, cursor.current);
        if (res.comments.length) merge(res.comments);
        cursor.current = res.latest_id;
      } catch {
        // Transient — the next tick retries. Never surface a polling failure as
        // an error banner; the comments already on screen are still valid.
      }
    }, POLL_MS);
    return () => clearInterval(id);
  }, [eventId, needsLogin, merge]);

  /** Apply a change to one comment wherever it sits in the tree. */
  const patch = useCallback((id: number, update: (c: Comment) => Comment) => {
    setThreads((prev) => prev.map((thread) => {
      const replies = (thread.replies ?? []).map((r) => (r.id === id ? update(r) : r));
      const base = thread.id === id ? update(thread) : thread;
      return { ...base, replies };
    }));
  }, []);

  /** Open the reply box under a thread. Row already resolves a reply's
   *  parent_id to the thread root, so this always receives a top-level id. */
  const openReply = useCallback((threadId: number) => {
    setReplyTo(threadId);
    setReplyDraft("");
  }, []);

  async function submit(parentId: number | null, text: string) {
    const body = text.trim();
    if (!body || posting) return;
    setPosting(true);
    setError("");
    try {
      const created = await postComment(eventId, body, parentId);
      merge([created]);
      if (created.id > cursor.current) cursor.current = created.id;
      if (parentId === null) setDraft("");
      else { setReplyDraft(""); setReplyTo(null); }
    } catch (e) {
      // 429 from the rate limiter lands here with the server's own wording.
      setError(e instanceof Error ? e.message : "Could not post comment");
    } finally {
      setPosting(false);
    }
  }

  async function vote(comment: Comment, value: 1 | -1) {
    const next = comment.my_vote === value ? 0 : value;   // click again to undo
    const before = comment.my_vote;
    // Optimistic: a vote button that waits for a round trip feels broken. The
    // server's counts overwrite these a moment later, and a failure rolls back.
    patch(comment.id, (c) => ({
      ...c,
      my_vote: next,
      likes: c.likes + (next === 1 ? 1 : 0) - (before === 1 ? 1 : 0),
      dislikes: c.dislikes + (next === -1 ? 1 : 0) - (before === -1 ? 1 : 0),
    }));
    try {
      const server = await voteComment(comment.id, next);
      patch(comment.id, (c) => ({
        ...c, likes: server.likes, dislikes: server.dislikes, my_vote: server.my_vote,
      }));
    } catch {
      patch(comment.id, (c) => ({
        ...c,
        my_vote: before,
        likes: c.likes - (next === 1 ? 1 : 0) + (before === 1 ? 1 : 0),
        dislikes: c.dislikes - (next === -1 ? 1 : 0) + (before === -1 ? 1 : 0),
      }));
    }
  }

  async function remove(id: number) {
    try {
      await deleteComment(id);
      // Mirror what the server now returns for a deleted row, rather than
      // dropping it — its replies still hang off it.
      patch(id, (c) => ({ ...c, deleted: true, body: null, user: null }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete comment");
    }
  }

  async function loadMore() {
    if (!beforeId || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await getComments(eventId, beforeId);
      setThreads((prev) => [...prev, ...page.comments]);   // older go beneath
      setHasMore(page.has_more);
      setBeforeId(page.next_before_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load more");
    } finally {
      setLoadingMore(false);
    }
  }

  if (needsLogin) {
    return (
      <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-400">
          WAR ROOM
        </h2>
        <p className="text-sm text-zinc-500">Sign in to read and join the discussion.</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        WAR ROOM
      </h2>

      <div className="mb-6">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="What do you make of this card?"
          rows={3}
          maxLength={2000}
          className="w-full resize-y rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-red-500/60 focus:outline-none"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-zinc-600">{draft.length}/2000</span>
          <button
            onClick={() => submit(null, draft)}
            disabled={posting || !draft.trim()}
            className="rounded-lg bg-red-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-40"
          >
            {posting ? "Posting…" : "Post"}
          </button>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      {loading && <p className="text-sm text-zinc-500">Loading comments…</p>}
      {!loading && threads.length === 0 && (
        <p className="text-sm text-zinc-500">No comments yet. Say something.</p>
      )}

      <ul className="space-y-3">
        {threads.map((thread) => (
          <li key={thread.id}
              className="rounded-lg border border-zinc-800 bg-black p-3 transition-colors hover:border-zinc-700">
            <Row comment={thread} isReply={false} meId={meId}
                 onVote={vote} onReply={openReply} onDelete={remove} />

            {(thread.replies?.length ?? 0) > 0 && (
              <ul className="mt-3 space-y-3 pl-4">
                {thread.replies!.map((reply) => (
                  <li key={reply.id}>
                    <Row comment={reply} isReply meId={meId}
                         onVote={vote} onReply={openReply} onDelete={remove} />
                  </li>
                ))}
              </ul>
            )}

            {replyTo === thread.id && (
              <div className="mt-3 pl-4">
                <textarea
                  value={replyDraft}
                  onChange={(e) => setReplyDraft(e.target.value)}
                  placeholder={`Reply to ${thread.user?.username ?? "this comment"}…`}
                  rows={2}
                  maxLength={2000}
                  autoFocus
                  className="w-full resize-y rounded-lg border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-red-500/60 focus:outline-none"
                />
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => submit(thread.id, replyDraft)}
                    disabled={posting || !replyDraft.trim()}
                    className="rounded-lg bg-red-600 px-3 py-1 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-40"
                  >
                    {posting ? "Posting…" : "Reply"}
                  </button>
                  <button onClick={() => setReplyTo(null)}
                          className="px-3 py-1 text-xs text-zinc-500 hover:text-zinc-300">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>

      {hasMore && (
        <button onClick={loadMore} disabled={loadingMore}
                className="mt-3 w-full rounded-lg border border-zinc-800 py-2 text-sm text-zinc-400 hover:border-red-500/60 hover:text-zinc-200 disabled:opacity-40">
          {loadingMore ? "Loading…" : "Load older comments"}
        </button>
      )}
    </section>
  );
}
