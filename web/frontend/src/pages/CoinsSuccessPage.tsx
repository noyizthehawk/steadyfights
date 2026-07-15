import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthError, getBalance } from "../api";
import { CoinIcon } from "../components/CoinIcon";

const MAX_TRIES = 8;
const DELAY_MS = 1500;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Stripe redirects here after a successful checkout. The webhook that actually
 *  credits the coins runs asynchronously and usually lands a beat AFTER this
 *  page loads, so we poll: if we know the pre-purchase balance (stashed before
 *  the redirect), we wait until the balance rises above it; otherwise we just
 *  read it once. Either way it resolves within a few seconds. */
export default function CoinsSuccessPage() {
  const [balance, setBalance] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const beforeRaw = sessionStorage.getItem("coins_before");
    const before = beforeRaw ? Number(beforeRaw) : null;

    (async () => {
      for (let i = 0; i < MAX_TRIES; i++) {
        try {
          const bal = await getBalance();
          if (cancelled) return;
          setBalance(bal);
          // credit landed (balance rose) — or we have no baseline to wait on
          if (before === null || bal > before) break;
        } catch (e) {
          if (e instanceof AuthError) return navigate("/login");
          // transient error — fall through and retry
        }
        if (i < MAX_TRIES - 1) await sleep(DELAY_MS);
      }
      if (!cancelled) {
        setConfirming(false);
        sessionStorage.removeItem("coins_before");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  return (
    <div className="w-full px-6 py-8 text-left">
      <div className="mx-auto max-w-md text-center">
        <div className="mt-8 flex justify-center">
          <CoinIcon size={56} className="shrink-0" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-white">Payment complete</h1>

        <div className="mt-6 rounded-xl border border-[#ffce4f33] bg-[#ffce4f0a] px-6 py-6">
          <div className="text-[10px] tracking-[0.3em] text-zinc-400">BALANCE</div>
          <div className="mt-3 flex items-center justify-center gap-3">
            <CoinIcon size={28} className="shrink-0" />
            <span
              style={{ fontFamily: "var(--font-display)" }}
              className="text-3xl text-[#ffd75e]"
            >
              {balance === null ? "…" : balance.toLocaleString()}
            </span>
          </div>
          {confirming && (
            <div className="mt-3 text-xs text-zinc-500">confirming your purchase…</div>
          )}
        </div>

        {!confirming && (
          <p className="mt-4 text-xs text-zinc-500">
            Coins not showing yet? They can take a few seconds — refresh in a moment.
          </p>
        )}

        <div className="mt-8 flex justify-center gap-3">
          <Link
            to="/rooms"
            className="rounded-lg bg-red-600 px-5 py-2.5 font-semibold text-white transition-colors hover:bg-red-500"
          >
            Back to rooms
          </Link>
          <Link
            to="/coins"
            className="rounded-lg border border-zinc-700 px-5 py-2.5 text-zinc-300 transition-colors hover:border-red-500/60 hover:text-white"
          >
            Buy more
          </Link>
        </div>
      </div>
    </div>
  );
}
