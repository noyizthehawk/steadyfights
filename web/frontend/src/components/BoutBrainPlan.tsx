import { useEffect, useState } from "react";
import { getBillingSummary, openBillingPortal, startSubscription, type BillingSummary } from "../api";
import { errorMessage } from "../lib/errorMessage";

/** The Bout Brain plan card on the Account page. One card, four states:
 *  active · cancelling (still active until period end) · payment failed · free.
 *  Dates and the card on file come live from Stripe via /api/billing/summary. */

const RUNDOWN = { fontFamily: "var(--font-rundown)" } as const;
const DISPLAY = { fontFamily: "var(--font-display)" } as const;

type Tone = "emerald" | "amber" | "red" | "zinc";
const TONE: Record<Tone, { dot: string; text: string }> = {
  emerald: { dot: "bg-emerald-400 shadow-[0_0_0_4px_#34d39922]", text: "text-emerald-300" },
  amber:   { dot: "bg-amber-400 shadow-[0_0_0_4px_#fbbf2422]",   text: "text-amber-300" },
  red:     { dot: "bg-[#d33a2c] shadow-[0_0_0_4px_#d33a2c33]",   text: "text-[#ff7a6b]" },
  zinc:    { dot: "bg-white/25",                                  text: "text-zinc-400" },
};

const date = (unix: number | null) =>
  unix ? new Date(unix * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : null;

const brand = (b: string) => (b === "amex" ? "Amex" : b.charAt(0).toUpperCase() + b.slice(1));

export function BoutBrainPlan() {
  const [plan, setPlan] = useState<BillingSummary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false); // a redirect to Stripe is in flight

  useEffect(() => {
    getBillingSummary().then(setPlan).catch((e) => setError(errorMessage(e)));
  }, []);

  async function go(open: () => Promise<string>) {
    setError("");
    setBusy(true);
    try {
      window.location.href = await open(); // full-page redirect to Stripe
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false); // only reset on failure — success navigates away
    }
  }

  // ---- derive the one state the card is in ----
  let tone: Tone = "zinc";
  let label = "Free";
  let lines: string[] = [];
  let primary: { text: string; onClick: () => void } | null = null;
  let secondary: { text: string; onClick: () => void } | null = null;
  const portal = () => go(openBillingPortal);
  const card = plan?.card ? `${brand(plan.card.brand)} •••• ${plan.card.last4}` : null;

  if (plan) {
    const ends = date(plan.period_end);
    if (plan.status === "active" && plan.cancel_at_period_end) {
      tone = "amber";
      label = "Ending";
      lines = [ends ? `Cancelled — you keep access until ${ends}` : "Cancelled — access until the end of this period",
               "Won't renew"];
      primary = { text: "Resume plan", onClick: portal };
    } else if (plan.status === "active" || plan.status === "trialing") {
      tone = "emerald";
      label = "Active";
      lines = [`${plan.price_label} · unlimited predictions`, ...(ends ? [`Renews ${ends}`] : []), ...(card ? [card] : [])];
      secondary = { text: "Manage billing", onClick: portal };
    } else if (plan.status === "past_due" || plan.status === "unpaid") {
      tone = "red";
      label = "Payment failed";
      lines = ["Your last payment didn't go through.", "Update your card to keep Bout Brain."];
      primary = { text: "Update card", onClick: portal };
    } else {
      label = plan.status === "canceled" ? "Cancelled" : "Free";
      lines = [`${plan.free_left} of ${plan.free_limit} free predictions left`,
               `Unlimited for ${plan.price_label}`];
      primary = { text: "Subscribe", onClick: () => go(startSubscription) };
      if (plan.status) secondary = { text: "Billing history", onClick: portal }; // they've paid before
    }
  }

  return (
    <section className="mt-6 rounded-2xl bg-zinc-900 p-6 text-left">
      <div className="flex items-center justify-between gap-4">
        <div className="text-[11px] leading-none text-white" style={DISPLAY}>BOUT BRAIN</div>
        {plan && (
          <div className="flex items-center gap-2">
            <span aria-hidden className={`block h-2 w-2 rounded-full ${TONE[tone].dot}`} />
            <span className={`text-xs italic ${TONE[tone].text}`} style={RUNDOWN}>{label}</span>
          </div>
        )}
      </div>

      {/* facts hang off the rundown's hairline red rule, one per line */}
      <div className="mt-5 space-y-1.5 border-l-2 border-[#d33a2c] pl-3 text-sm italic text-zinc-300" style={RUNDOWN}>
        {plan
          ? lines.map((l) => <p key={l}>{l}</p>)
          : !error && (
              <>
                <div className="h-3.5 w-48 animate-pulse rounded bg-zinc-800" />
                <div className="h-3.5 w-32 animate-pulse rounded bg-zinc-800" />
              </>
            )}
      </div>

      {(primary || secondary) && (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {primary && (
            <button
              onClick={primary.onClick}
              disabled={busy}
              className="rounded-lg bg-[#d33a2c] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#e2463a] disabled:opacity-55"
            >
              {busy ? "Opening…" : primary.text}
            </button>
          )}
          {secondary && (
            <button
              onClick={secondary.onClick}
              disabled={busy}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 transition-colors hover:border-zinc-500 hover:text-white disabled:opacity-55"
            >
              {busy && !primary ? "Opening…" : secondary.text}
            </button>
          )}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-[#ff7a6b]">{error}</p>}
      <p className="mt-5 text-[11px] text-zinc-600">Payments, cards and invoices are handled securely by Stripe.</p>
    </section>
  );
}
