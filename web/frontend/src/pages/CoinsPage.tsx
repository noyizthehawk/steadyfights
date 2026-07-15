import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthError, buyCoins, getBalance, type CoinPack } from "../api";
import { CoinIcon } from "../components/CoinIcon";
import { errorMessage } from "../lib/errorMessage";


const PACKS: { id: CoinPack; coins: number; price: string; tag?: string }[] = [
  { id: "small", coins: 1000, price: "$4.99" },
  { id: "medium", coins: 5000, price: "$9.99", tag: "BEST VALUE" },
  { id: "large", coins: 10000, price: "$19.99" },
];

export default function CoinsPage() {
  const [balance, setBalance] = useState<number | null>(null);
  const [buying, setBuying] = useState<CoinPack | null>(null); // which pack is redirecting
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    getBalance()
      .then(setBalance)
      .catch((e) => {
        if (e instanceof AuthError) navigate("/login");
      });
  }, [navigate]);

  async function handleBuy(pack: CoinPack) {
    setError("");
    setBuying(pack);
    try {
      const url = await buyCoins(pack);
      // stash the current balance so /success can poll until the webhook credits
      // the coins (the redirect beats the webhook, so the balance lags briefly)
      sessionStorage.setItem("coins_before", String(balance ?? ""));
      window.location.href = url;
    } catch (e) {
      if (e instanceof AuthError) return navigate("/login");
      setError(errorMessage(e));
      setBuying(null); // only reset on failure,on success we're leaving the page
    }
  }

  return (
    <div className="w-full px-6 py-8 text-left">
      <div className="mx-auto max-w-3xl">
        <Link to="/rooms" className="text-sm text-zinc-400 hover:text-white">
          Back to the Lobby
        </Link>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="m-0 text-2xl font-bold text-white">Buy Coins</h1>
          {balance !== null && (
            <span className="ml-auto flex items-center gap-2 rounded-full border border-[#ffce4f66] bg-[#ffce4f14] px-3 py-1.5 text-[#ffd75e]">
              <CoinIcon size={14} className="shrink-0" />
              <span style={{ fontFamily: "var(--font-display)" }} className="text-[11px]">
                {balance.toLocaleString()}
              </span>
            </span>
          )}
        </div>

        <p className="mt-2 text-sm text-zinc-400">
          Coins buy you into rooms and are for bragging rights, casual
        </p>

        {error && <p className="error mt-4">{error}</p>}

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {PACKS.map((pack) => (
            <div
              key={pack.id}
              className={`relative flex flex-col items-center rounded-xl border bg-zinc-900 px-4 py-8 text-center ${
                pack.tag ? "border-[#ffce4f66]" : "border-zinc-800"
              }`}
            >
              {pack.tag && (
                <span
                  style={{ fontFamily: "var(--font-display)" }}
                  className="absolute -top-2 rounded-full bg-[#ffce4f] px-2 py-0.5 text-[8px] text-black"
                >
                  {pack.tag}
                </span>
              )}
              <CoinIcon size={40} className="shrink-0" />
              <div
                style={{ fontFamily: "var(--font-display)" }}
                className="mt-4 text-lg text-[#ffd75e]"
              >
                {pack.coins.toLocaleString()}
              </div>
              <div className="mt-1 text-xs tracking-widest text-zinc-500">COINS</div>
              <button
                onClick={() => handleBuy(pack.id)}
                disabled={buying !== null}
                className="mt-6 w-full rounded-lg bg-red-600 px-4 py-2.5 font-semibold text-white transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {buying === pack.id ? "Redirecting…" : pack.price}
              </button>
            </div>
          ))}
        </div>

        <p className="mt-6 text-xs text-zinc-500">
          Payments are handled securely by Stripe. You'll return here once it's done.
        </p>
      </div>
    </div>
  );
}
