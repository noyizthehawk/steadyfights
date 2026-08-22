"""UFC news endpoint, backed by NewsAPI and Redis-cached."""
import json

from fastapi import APIRouter, HTTPException
from redis import RedisError

from ..redis_client import redis_client
from ..config import newsapi, NEWS_TTL

router = APIRouter()


@router.get("/api/news")
def get_news(q: str = "UFC"):
    if newsapi is None:
        raise HTTPException(status_code=503, detail="News API not configured (set NEWS_API_KEY).")

    # normalize the query for the key so "UFC" and "ufc" share one cached entry
    cache_key = f"news:{q.lower()}"

    # serve cached news if present; on a miss OR a Redis outage, fall through to
    # the live API so the cache is never a hard dependency.
    if redis_client is not None:
        try:
            cached = redis_client.get(cache_key)
            if cached is not None:
                return json.loads(cached)
        except RedisError:
            pass    # don't leak Redis errors

    query = q if "ufc" in q.lower() else f"{q} UFC"   # keep results on-topic
    try:
        result = newsapi.get_everything(
            q=query,
            language="en",
            sort_by="publishedAt",
            page_size=10,
        )
    except Exception:
        # Don't leak provider internals; just report it's unavailable.
        raise HTTPException(status_code=502, detail="News provider unavailable.")

    
    seen_urls = set()
    seen_titles = set()
    articles = []
    for a in result.get("articles", []):
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

    payload = {"query": q, "articles": articles}

    # cache only successful responses (the 502/503 paths above never reach here)
    if redis_client is not None:
        try:
            redis_client.set(cache_key, json.dumps(payload), ex=NEWS_TTL)
        except RedisError:
            pass

    return payload
