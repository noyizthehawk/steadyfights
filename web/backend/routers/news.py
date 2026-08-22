"""UFC news endpoint, backed by NewsAPI and Redis-cached."""
import json

from fastapi import APIRouter, HTTPException
from redis import RedisError

from ..redis_client import redis_client
from ..config import newsapi, NEWS_TTL

router = APIRouter()


_QUERY = (
    '(UFC OR MMA OR "mixed martial arts" OR "Dana White" OR Bellator OR PFL) '
    'AND (fight OR fighter OR octagon OR knockout OR submission OR bout OR '
    '"fight night" OR welterweight OR lightweight OR heavyweight OR bantamweight OR '
    'featherweight OR flyweight OR middleweight OR championship OR "title fight")'
)


_STRONG = ("mixed martial arts", "octagon", "dana white", "bellator", "pfl",
           "one championship", "mma")
_CONTEXT = ("fight", "fighter", "bout", "knockout", " ko ", "submission",
            "welterweight", "lightweight", "heavyweight", "bantamweight",
            "featherweight", "flyweight", "middleweight", "champion", "title",
            "octagon", "main event", "fight night")
# Known non-MMA uses of "UFC" to drop outright.
_BLOCK = ("que choisir", "union fédérale", "consommateurs")


def _is_mma(article: dict) -> bool:
    text = f"{article.get('title') or ''} {article.get('description') or ''}".lower()
    if any(b in text for b in _BLOCK):
        return False
    if any(s in text for s in _STRONG):
        return True
    # otherwise "ufc" only counts with a fighting-context word alongside it
    return "ufc" in text and any(c in text for c in _CONTEXT)


@router.get("/api/news")
def get_news(q: str = "UFC"):
    if newsapi is None:
        raise HTTPException(status_code=503, detail="News API not configured (set NEWS_API_KEY).")

    cache_key = "news:mma"

    # serve cached news if present; on a miss OR a Redis outage, fall through to
    # the live API so the cache is never a hard dependency.
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
            if cached is not None:
                return json.loads(cached)
        except RedisError:
            pass    # don't leak Redis errors

    try:
        result = newsapi.get_everything(
            q=_QUERY,
            language="en",
            sort_by="publishedAt",
            page_size=40,   # over-fetch; the MMA post-filter trims it down
        )
    except Exception:
        # Don't leak provider internals; just report it's unavailable.
        raise HTTPException(status_code=502, detail="News provider unavailable.")

    seen_urls = set()
    seen_titles = set()
    articles = []
    for a in result.get("articles", []):
        if not _is_mma(a):
            continue    # drop non-MMA noise
        url = a.get("url")
        title = a.get("title")
        title_key = (title or "").strip().lower()
        if url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        articles.append({
            "title": title,
            "url": url,
            "source": (a.get("source") or {}).get("name"),
            "published_at": a.get("publishedAt"),
            "image": a.get("urlToImage"),
        })
        if len(articles) >= 12:
            break

    payload = {"query": q, "articles": articles}

    # cache only successful responses (the 502/503 paths above never reach here)
    if redis_client is not None:
        try:
            redis_client.set(cache_key, json.dumps(payload), ex=NEWS_TTL)
        except RedisError:
            pass

    return payload
