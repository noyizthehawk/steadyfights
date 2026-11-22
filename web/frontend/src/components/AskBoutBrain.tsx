import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  askBout,
  AuthError,
  getBoutAskMeta,
  PaywallError,
  startSubscription,
  type BoutAnswer,
  type BoutAskMeta,
} from "../api";

/** Ask Bout Brain: one question at a time about the matchup on screen,
 *  answered from our own stats. Not a chat; each question stands alone, so
 *  earlier answers just stack underneath. */

const RED = "#d33a2c";
const BLUE = "#60a5fa";
const MONO = { fontFamily: "var(--mono)" } as const;
const RUNDOWN = { fontFamily: "var(--font-rundown)" } as const;
const LABEL = "text-[9px] uppercase tracking-widest text-zinc-500";

function lastName(n: string) {
  const parts = n.trim().split(/\s+/);
  return parts[parts.length - 1];
}

function Answer({ a, fighterA, fighterB }: { a: BoutAnswer; fighterA: string; fighterB: string }) {
  const edge =
    a.edge === "a" ? { name: lastName(fighterA), color: RED }
    : a.edge === "b" ? { name: lastName(fighterB), color: BLUE }
    : a.edge === "even" ? { name: "Even", color: "#a1a1aa" }
    : null;
  return (
    <div className="border-l-2 py-1 pl-3" style={{ borderColor: edge?.color ?? "#3f3f46" }}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[11px] text-zinc-500" style={MONO}>{a.question}</span>
        {edge && (
          <span className="shrink-0 text-[10px] uppercase tracking-wider" style={{ ...MONO, color: edge.color }}>
            {a.edge === "even" ? "Even" : `Edge ${edge.name}`}
          </span>
        )}
      </div>
      <p className="mt-1 text-[14px] italic leading-relaxed text-zinc-200" style={RUNDOWN}>{a.answer}</p>
    </div>
  );
}

/** `framed` draws the top rule used inside the predictor's result card; the
 *  event page embeds it in its own panel and turns that off. */
export function AskBoutBrain({ fighterA, fighterB, framed = true }: { fighterA: string; fighterB: string; framed?: boolean }) {
  const navigate = useNavigate();
  const [meta, setMeta] = useState<BoutAskMeta | null>(null);
  const [answers, setAnswers] = useState<BoutAnswer[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [paywall, setPaywall] = useState("");
  const [subscribing, setSubscribing] = useState(false);

  useEffect(() => {
    getBoutAskMeta().then(setMeta).catch(() => {});
  }, []);

  async function ask(q: string) {
    q = q.trim();
    if (!q || pending) return;
    setError("");
    setPending(q);
    try {
      const a = await askBout(fighterA, fighterB, q);
      setAnswers((prev) => [a, ...prev]);
      setMeta((m) => (m ? { ...m, remaining: a.remaining } : m));
      setQuestion("");
    } catch (e: unknown) {
      if (e instanceof AuthError) navigate("/login");
      else if (e instanceof PaywallError) {
        setPaywall(e.message);
        setMeta((m) => (m ? { ...m, remaining: 0 } : m));
      } else setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setPending(null);
    }
  }

  async function subscribe() {
    setSubscribing(true);
    try {
      window.location.href = await startSubscription();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not start subscription");
      setSubscribing(false);
    }
  }

  const asked = new Set(answers.map((a) => a.question));
  const chips = (meta?.suggested ?? []).filter((q) => !asked.has(q));
  const out = meta !== null && meta.remaining <= 0;

  return (
    <div className={framed ? "border-t border-zinc-800 px-4 py-3 sm:px-5" : "p-3"}>
      <div className="mb-2.5 flex items-baseline justify-between gap-3">
        <span className={LABEL}>Ask Bout Brain</span>
        {meta && (
          <span className="text-[10px] text-zinc-500" style={MONO}>
            {meta.remaining}/{meta.limit} left today
          </span>
        )}
      </div>

      {!out && chips.length > 0 && (
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          {chips.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => ask(q)}
              disabled={pending !== null}
              className="rounded-md border border-zinc-700 bg-transparent px-2.5 py-1.5 text-[11px] text-zinc-300 transition-colors hover:border-zinc-500 hover:text-white disabled:opacity-40"
              style={MONO}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {!out && (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={200}
            placeholder={`Ask about ${lastName(fighterA)} vs ${lastName(fighterB)}`}
            className="min-w-0 flex-1 rounded-md border border-zinc-700 bg-black px-3 py-2 text-[13px] text-white placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
            style={MONO}
          />
          <button
            type="submit"
            disabled={pending !== null || !question.trim()}
            className="shrink-0 rounded-md px-3.5 text-[11px] font-semibold uppercase tracking-wider text-black disabled:opacity-40"
            style={{ ...MONO, background: RED }}
          >
            Ask
          </button>
        </form>
      )}

      {out && (
        <div className="rounded-md border border-zinc-800 px-3 py-2.5">
          <p className="text-[13px] text-zinc-300" style={RUNDOWN}>
            {paywall ||
              (meta?.subscribed
                ? "That's your questions for today. Back tomorrow."
                : "You're out of free questions today.")}
          </p>
          {!meta?.subscribed && (
            <button
              type="button"
              onClick={subscribe}
              disabled={subscribing}
              className="mt-2 rounded-md px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-black disabled:opacity-50"
              style={{ ...MONO, background: RED }}
            >
              {subscribing ? "Redirecting…" : "Subscribe · 30 a day"}
            </button>
          )}
        </div>
      )}

      {error && <p className="mt-2 text-[12px] text-[#ff7a6b]" style={MONO}>{error}</p>}

      {(pending || answers.length > 0) && (
        <div className="mt-3 flex flex-col gap-3">
          {pending && (
            <div className="border-l-2 border-zinc-700 py-1 pl-3">
              <span className="text-[11px] text-zinc-500" style={MONO}>{pending}</span>
              <p className="mt-1 animate-pulse text-[13px] text-zinc-500" style={MONO}>reading the tape…</p>
            </div>
          )}
          {answers.map((a, i) => (
            <Answer key={`${a.question}-${i}`} a={a} fighterA={fighterA} fighterB={fighterB} />
          ))}
        </div>
      )}
    </div>
  );
}
