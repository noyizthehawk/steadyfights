"""Central config: env vars, constants, and the third-party clients built from
them. Imported by routers and services so settings live in one place."""
import os

import stripe
from apify_client import ApifyClient
from newsapi import NewsApiClient

from . import PROJECT_ROOT  # noqa: F401  (re-exported; also ensures sys.path set)

# Cache TTLs (seconds)
LEADERBOARD_TTL = 60
NEWS_TTL = 600  # 10 minutes

# ufc.com scraping
BASE = "https://www.ufc.com"
headers = {"User-Agent": "Mozilla/5.0"}

# News API
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
newsapi = NewsApiClient(api_key=NEWS_API_KEY) if NEWS_API_KEY else None

# FUTURE FIGHTS API
UFC_API_KEY = os.getenv("UFC_API_KEY")
client = ApifyClient(UFC_API_KEY)



COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")

# Admin / billing
SETTLE_SECRET = os.getenv("SETTLE_SECRET")
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
# Where Stripe sends users back after checkout. In prod (FastAPI serves the
# frontend) this is the app's own public URL — set FRONTEND_URL on Railway.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
