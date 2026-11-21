// Privacy policy. Plain-English and specific to what the app actually stores —
// if you add a tracker, a new third party, or a new kind of user data, update this.
//
// Typography note: the global h1/h2 rule in index.css forces the pixel display
// font. That suits page titles but makes long-form text look like a game menu,
// so section headings here are <h3>s in the rundown face instead.
const CONTACT_EMAIL = "steadycorporation@icloud.com";
const LAST_UPDATED = "November 21, 2026";

const READ = { fontFamily: "var(--font-rundown)" } as const;

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="grid grid-cols-[2.25rem_1fr] gap-x-4 border-t border-zinc-800/80 py-7 sm:grid-cols-[3rem_1fr]">
      <span className="pt-[3px] text-xs tabular-nums text-zinc-600">{String(n).padStart(2, "0")}</span>
      <div>
        <h3 className="text-[17px] font-medium text-white">{title}</h3>
        <div className="mt-3 space-y-3 text-[15px] leading-7 text-zinc-400">{children}</div>
      </div>
    </section>
  );
}

function Item({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <li className="relative pl-4 before:absolute before:left-0 before:top-[0.8em] before:h-px before:w-2 before:bg-zinc-600">
      <span className="font-medium text-zinc-200">{term}.</span> {children}
    </li>
  );
}

const A = ({ href, children }: { href: string; children: React.ReactNode }) => (
  <a
    href={href}
    className="text-zinc-200 underline decoration-zinc-600 underline-offset-4 transition-colors hover:decoration-zinc-300"
    {...(href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}
  >
    {children}
  </a>
);

export default function PrivacyPage() {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 text-left" style={READ}>
      <div className="text-[10px] tracking-[0.3em] text-zinc-500">LEGAL</div>
      <h1 className="!mb-3 !mt-3">Privacy</h1>
      <p className="text-xs text-zinc-500">Last updated {LAST_UPDATED}</p>

      <p className="mb-10 mt-8 text-[17px] leading-8 text-zinc-300">
        SteadyFights is run by STEADYCORPORATION in Canada. This page covers what we collect when
        you use the site, why, who we share it with, and what you can ask us to do with it.
        We don't sell your data, and we don't run ads or third-party tracking.
      </p>

      <Section n={1} title="What we collect">
        <ul className="space-y-3">
          <Item term="Account details">Your email, username, and password. We never store the
            password itself, only a one-way hash of it.</Item>
          <Item term="Profile photo">If you choose to upload one.</Item>
          <Item term="Activity">Your picks and predictions, rooms you create or join, comments and
            votes, friends, coin history, and any room covers or reports you submit.</Item>
          <Item term="Subscription">Whether your Bout Brain subscription is active, and the
            customer ID Stripe assigns you.</Item>
          <Item term="IP address">Used briefly to rate-limit things like login attempts. It sits in
            a short-lived counter that expires on its own and is never stored with your account.</Item>
        </ul>
      </Section>

      <Section n={2} title="Payments">
        <p>
          Payments are processed by Stripe. Your card details go directly to Stripe and never
          reach our servers. We receive only confirmation that a payment succeeded, what you
          bought, and your Stripe customer ID. Stripe's handling of your data is covered by
          the <A href="https://stripe.com/privacy">Stripe Privacy Policy</A>.
        </p>
        <p>
          Coins are for entertainment only. They can't be withdrawn, redeemed for cash, or
          exchanged for prizes.
        </p>
      </Section>

      <Section n={3} title="Cookies">
        <p>
          We use two cookies, both only to keep you signed in: a short-lived session cookie and a
          longer-lived refresh cookie. Scripts on the page can't read either of them. We don't use
          advertising or analytics cookies.
        </p>
      </Section>

      <Section n={4} title="What other users can see">
        <p>
          Your username, profile photo, picks, comments, room activity, and leaderboard position
          are visible to other users. When you send a friend request, the person you invite
          receives an email that includes your email address.
        </p>
      </Section>

      <Section n={5} title="Services we use">
        <p>We share data only with the services needed to run the site:</p>
        <ul className="space-y-3">
          <Item term="Stripe">Payments and subscriptions.</Item>
          <Item term="Railway">Hosting for our servers and database.</Item>
          <Item term="Cloudflare">DNS, and storage for uploaded images.</Item>
          <Item term="Resend">Delivery of our emails.</Item>
        </ul>
        <p>Some of these process data outside Canada, including in the United States.</p>
      </Section>

      <Section n={6} title="How long we keep it">
        <p>
          We keep your data for as long as your account exists. Payment records may be kept
          longer where the law requires us to retain financial records.
        </p>
      </Section>

      <Section n={7} title="Your choices">
        <p>
          You can ask for a copy of your data, ask us to correct it, or ask us to delete your
          account by emailing <A href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</A>. We'll
          respond within 30 days. You can cancel a subscription at any time from your Account page.
        </p>
      </Section>

      <Section n={8} title="Age">
        <p>SteadyFights is not intended for anyone under 18.</p>
      </Section>

      <Section n={9} title="Changes to this policy">
        <p>
          If this policy changes, we'll update the date at the top. For significant changes, we'll
          also let you know by email.
        </p>
      </Section>
    </div>
  );
}
