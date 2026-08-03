# 🥊 SteadyFights

> A full-stack UFC prediction & pick'em platform — make picks, compete on leaderboards, join coin-staked prize rooms, and explore fighter analytics powered by a calibrated machine-learning model.

**Live:** [steadyfights.com](https://steadyfights.com)

---

## What it is

SteadyFights is a deployed web app where users predict UFC fights, compete against friends and a global leaderboard, and stake a virtual coin currency in prize "rooms." Every fighter has an analytics page — career score, tale-of-the-tape, recent form, style profile — and matchups are backed by an ML model that outputs **calibrated** win probabilities, not just a pick.

It's a single, real product that spans the stack: a machine-learning pipeline, a scraping/data pipeline, authentication, payments, a virtual economy, caching, object storage, transactional email, and database migrations — deployed on its own domain.

## Tech stack

| Layer | Tech |
|---|---|
| **Backend** | Python, FastAPI, SQLAlchemy, Alembic, Pydantic |
| **Frontend** | React, TypeScript, Vite, Tailwind CSS |
| **Database** | PostgreSQL (prod) · SQLite (dev) — env-driven |
| **ML** | scikit-learn, XGBoost, pandas, NumPy |
| **Infra / services** | Railway (hosting), Cloudflare (DNS + R2 object storage), Redis, Stripe (payments), Resend (email), GitHub Actions (cron) |
| **Data pipeline** | Playwright + BeautifulSoup (scraping ufc.com) |

## Features

- **ML fight predictions** with calibrated probabilities and a "tale of the tape" explaining the top factors
- **Pick'em** — pick winners for upcoming cards; picks lock before the event
- **Prize rooms** — create/join rooms with a coin buy-in; the pot is split among the top scorers
- **Virtual coin economy** — buy coins via Stripe, staked in rooms, paid out on settlement
- **Fighter analytics pages** — career score (0–100), recent form (last 5), tale-of-the-tape stats, career-phase breakdown, and a global fighter search
- **Social** — friends, avatars (custom uploads), usernames, worldwide + per-room leaderboards
- **Automated data pipeline** — weekly scrape of upcoming cards and auto-settling of finished events via scheduled jobs

---

## Notable engineering decisions

The parts I'd actually talk about in an interview:

### Machine learning done honestly
- **No data leakage.** The train/test split is **temporal** (train on the past, test on the most recent fights) — mirroring reality, where you only ever predict *future* fights. A random split would leak future information and inflate the score.
- **Calibrated probabilities.** The ensemble (XGBoost + RandomForest + LogisticRegression, soft-voting) is wrapped in `CalibratedClassifierCV`, because the app *shows users a probability* — an uncalibrated "80%" that isn't really 80% is worse than useless. Calibration is verified with a reliability table.
- **~62% accuracy on a temporal holdout** — modest by design. MMA is extremely high-variance; the betting market itself only picks winners ~65% straight-up. The value is an honest, leakage-free number with well-calibrated probabilities, not a vanity figure.
- **Found and fixed a subgroup bias.** A suspicious prediction led to a holdout test that revealed the model was near coin-flip (53%) when *fading a finisher*. Traced it to `striking_differential` — a feature collinear with stats already in the model that unfairly penalized finishers (short brawls → negative differential). Removing it lifted the finisher-underdog bucket from 52.6% → 55.9% at **zero overall cost**.

### An append-only coin ledger
Balances are never stored as a mutable number. Every coin movement is an **immutable row** in a ledger, and a balance is `SUM(amount)`. This is the double-entry-accounting approach: fully auditable, and impossible to corrupt with a lost update. Stripe webhooks credit coins **idempotently** via a unique `external_id`, so a webhook delivered twice (which Stripe does) can't double-credit.

### Authentication with real tradeoffs
JWT stored in an **httpOnly cookie** (so XSS can't read the token), bcrypt password hashing, a **constant-time login** (verifies against a dummy hash on the unknown-user path so response time can't reveal which accounts exist), account-enumeration-aware sign-up, an env-driven `Secure` cookie flag, and case-insensitive usernames enforced by a functional unique index.

### Rate limiting: fail open, admin gate: fail closed
The Redis rate limiter **fails open** (Redis down → requests pass) to protect availability, while the admin/cron token gate **fails closed** (misconfigured → endpoint disabled) to protect privilege. Same codebase, opposite failure modes, chosen deliberately.

### Other decisions
- **Cache-aside with Redis** for the leaderboard and news (expensive queries cached with a TTL; every Redis call wrapped so a cache failure degrades to "slower," never "broken").
- **Alembic migrations** — including a data-backfill migration (adding a required `username` to a table that already had live users).
- **Name normalization** (`unidecode`) so scraped names with accents (`Rakić`, `Błachowicz`) match the ASCII names in the model's data.
- **Single-service deploy** — FastAPI serves the built React app from one origin, so there's no CORS in prod and one thing to deploy.

---

## The ML & data-analysis research

Before the app, the project started as a data-science investigation into what actually predicts MMA outcomes. The predictive model is built on those findings.

- **Fighters peak early.** Win rate declines monotonically across career stages (60.6% in fights 1–5 → 44.2% by fight 16+) — career longevity ≠ sustained performance.
- **Don't bet against the older fighter.** In competitive matchups, age correlates *positively* with winning (a proxy for experience/durability), up to a point.
- **Wrestling is a structural edge.** Wrestlers beat strikers ~57.6% of the time in cross-style bouts.
- **Reach matters only at the extremes** (>20 cm gap), and **size effects are division-dependent** (compact frames can win in flyweight; reach dominates at heavyweight).

Charts and full write-ups live in [`analysis_images_part_1/`](analysis_images_part_1/) and [`part_2/`](part_2/).

The predictor (`part_2/Prediction_model.py`) engineers matchup features — Elo (with inactivity decay), rolling 3/5-fight form, opponent-strength-adjusted performance, KMeans style clusters, and physicals — as **fighter-difference** vectors, and augments training with mirrored rows so `predict(A, B) == 1 − predict(B, A)`.

---

## Running locally

**Backend**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional: create a .env with JWT_SECRET (and Stripe/Resend/R2/Redis keys for those features)
alembic upgrade head
uvicorn web.backend.app:app --reload --reload-dir web/backend
```

**Frontend**
```bash
cd web/frontend
npm install
npm run dev            # dev server on :5173, proxies API to :8000
# npm run build        # production build (committed dist/ is what prod serves)
```

The app runs without Redis, Stripe, R2, or Resend configured — those features degrade gracefully when their env vars are absent (no caching/rate-limiting, no payments, no uploads, no email).

---

## Roadmap

Planned:
- **Multi-outcome picks** — pick not just the winner but the **method (KO/Sub/Decision) and round**, with tiered scoring
- **Model-vs-market track record** — measure the model against closing betting odds (does it beat "always pick the favorite"?) and surface the results publicly
- **Fight reminders** — email users before their picks lock
- **Live fight night** — real-time leaderboard/pick updates via WebSockets

Known and deliberately deferred (documented, not hidden):
- Scraper hardening — a fight `status` to distinguish cancelled vs. pending and stop re-scraping settled events
- Session revocation (`token_version`) for "log out everywhere"
- A `SELECT ... FOR UPDATE` lock to close a low-probability coin-overdraft race under concurrent room joins

---

*Built as a portfolio project. Payments run in Stripe test mode; not intended for real-money gambling.*
