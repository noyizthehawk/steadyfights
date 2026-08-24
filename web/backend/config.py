"""Central config: env vars, constants, and the third-party clients built from
them. Imported by routers and services so settings live in one place."""
import os

import stripe
from apify_client import ApifyClient
from newsapi import NewsApiClient
from dotenv import load_dotenv

from . import PROJECT_ROOT
  # noqa: F401  (re-exported; also ensures sys.path set)
load_dotenv() 

# Cache TTLs (seconds)
LEADERBOARD_TTL = 60
NEWS_TTL = 600  # 10 minutes

# ufc.com scraping
BASE = "https://www.ufc.com"
headers = {"User-Agent": "Mozilla/5.0"}

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# News API
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
newsapi = NewsApiClient(api_key=NEWS_API_KEY) if NEWS_API_KEY else None

# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Transcript fetching: YouTube blocks the transcript endpoint from datacenter IPs
# (Railway), so in prod we route youtube-transcript-api through a residential
# proxy. Unset locally -> direct fetch. Webshare is the library's first-class
# integration; YT_PROXY_URL is a generic http/https proxy fallback.
WEBSHARE_PROXY_USERNAME = os.getenv("WEBSHARE_PROXY_USERNAME")
WEBSHARE_PROXY_PASSWORD = os.getenv("WEBSHARE_PROXY_PASSWORD")
YT_PROXY_URL = os.getenv("YT_PROXY_URL")


YOUTUBE_CHANNEL_IDS = [
    c.strip() for c in os.getenv(
        "YOUTUBE_CHANNEL_IDS",
        ",".join([
            "UC7LzaJA-R2E52qzd5GW-kpg",  # LucasTracyMMA1
            "UCQAMRRo7fPbQMzlJWOexlZg",  # Bedtime MMA
            "UCIhQvpinmS8Eq6PrQ021DKQ",  # THE MMA GURU (@the-mma-guru)
        ]),
    ).split(",") if c.strip()
]
VIDEOS_TTL = 1800  # 30 minutes

# FUTURE FIGHTS API
UFC_API_KEY = os.getenv("UFC_API_KEY")
client = ApifyClient(UFC_API_KEY)

EMAIL_FROM = os.getenv("EMAIL_FROM")

# Cloudflare R2 (S3-compatible) for avatar uploads. R2_PUBLIC_URL is the bucket's
# public base (e.g. https://pub-xxxx.r2.dev) used to build the stored image URL.
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")

# Admin / billing
SETTLE_SECRET = os.getenv("SETTLE_SECRET")
stripe.api_key = os.getenv("STRIPE_API_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
# Where Stripe sends users back after checkout. In prod (FastAPI serves the
# frontend) this is the app's own public URL — set FRONTEND_URL on Railway.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
