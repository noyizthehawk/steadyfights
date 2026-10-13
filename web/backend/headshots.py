"""Fighter pictures, in priority order.

1. The event-card headshot already stored on UFCFight (img_a / img_b).
2. The fighter's ufc.com athlete page — the same standing studio shot.
3. Their Wikipedia article's photo on Wikimedia Commons. Every Commons file is
   reusable commercially, but the licence requires a credit, so the author,
   licence and file page are stored alongside the URL and shown in the UI.
4. Nothing — the UI draws an initials placeholder.

2 and 3 are slow network calls, so they never run inside a request: the
backfill (scripts/backfill_headshots.py) fills FighterHeadshot ahead of time,
and lookup() only ever reads the database.
"""
import logging
import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
from sqlalchemy import or_

from .models import FighterHeadshot, UFCEvent, UFCFight
from part_2.career import normalize_name

log = logging.getLogger(__name__)

_WIKI_HEADERS = {"User-Agent": "steadyfights/1.0 (fighter cards; image credits shown in app)"}
_UFC_HEADERS = {"User-Agent": "Mozilla/5.0"}

_COMMONS_WIDTH = 600


def ufc_slug(name: str) -> str:
    """'Georges St-Pierre' -> 'georges-st-pierre', 'José Aldo' -> 'jose-aldo'."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    ascii_name = re.sub(r"['.]", "", ascii_name.lower())       # O'Malley -> omalley
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")


def fetch_ufc(name: str) -> str | None:
    """The standing shot from ufc.com/athlete/<slug>, or None.
    """
    try:
        resp = requests.get(f"https://www.ufc.com/athlete/{ufc_slug(name)}",
                            headers=_UFC_HEADERS, timeout=20)
    except requests.RequestException as e:
        log.info("ufc.com fetch failed for %s: %s", name, e)
        return None
    if resp.status_code != 200:
        return None
    img = BeautifulSoup(resp.text, "html.parser").select_one("img.hero-profile__image")
    src = img.get("src") if img else None
    if not src or "silhouette" in src.lower() or "no-profile" in src.lower():
        return None
    return src


def fetch_commons(name: str) -> dict | None:
    """The lead photo of the fighter's English Wikipedia article, with the
    credit its licence requires, or None.

    The article must describe a mixed martial artist: plenty of fighters share
    a name with a footballer or a politician, and a confident wrong face is
    worse than the placeholder."""
    try:
        # Shared names live at "Name (fighter)" with "Name" as a disambiguation
        # page (e.g. Matt Hughes), so try the plain title, then that one.
        file_name = None
        for title in (name, f"{name} (fighter)"):
            page = requests.get("https://en.wikipedia.org/w/api.php", headers=_WIKI_HEADERS, timeout=20, params={
                "action": "query", "format": "json", "redirects": 1, "titles": title,
                "prop": "pageimages|description|pageprops", "piprop": "name",
            }).json()
            p = next(iter(page["query"]["pages"].values()))
            if "missing" in p or "disambiguation" in p.get("pageprops", {}):
                continue
            if "mixed martial art" not in (p.get("description") or "").lower():
                continue
            file_name = p.get("pageimage")
            break
        if not file_name:
            return None

        info = requests.get("https://commons.wikimedia.org/w/api.php", headers=_WIKI_HEADERS, timeout=20, params={
            "action": "query", "format": "json", "titles": f"File:{file_name}",
            "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": _COMMONS_WIDTH,
        }).json()
        ii = next(iter(info["query"]["pages"].values())).get("imageinfo", [None])[0]
    except (requests.RequestException, ValueError, KeyError, StopIteration) as e:
        log.info("commons lookup failed for %s: %s", name, e)
        return None
    if not ii:
        return None

    meta = ii.get("extmetadata", {})
    # Artist is HTML (usually a link to the user page); keep just the text
    author = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
    if not author or author.lower().startswith("unknown"):
        author = None                       # the UI credits "Wikimedia Commons"
    license_name = meta.get("LicenseShortName", {}).get("value")
    if not license_name:
        return None                         # can't credit it properly -> don't use it
    return {
        "image_url": ii.get("thumburl") or ii.get("url"),
        "credit_author": author,
        "credit_license": license_name,
        "credit_url": ii.get("descriptionurl"),
    }


def _event_details(db, norms: set[str]) -> dict[str, dict]:
    """Newest event-card headshot, flag and country per normalized name, in ONE
    query. Each field is taken from the newest row that HAS it, so a card
    missing a flag doesn't blank out a flag from the fight before.

    Names are matched after normalize_name in Python, not in SQL, because the
    event scrape and the career data spell some names differently (accents)."""
    rows = (
        db.query(UFCFight.fighter_a, UFCFight.img_a, UFCFight.flag_a, UFCFight.country_a,
                 UFCFight.fighter_b, UFCFight.img_b, UFCFight.flag_b, UFCFight.country_b)
        .join(UFCEvent, UFCFight.event_id == UFCEvent.id)
        .filter(or_(UFCFight.img_a.isnot(None), UFCFight.img_b.isnot(None),
                    UFCFight.flag_a.isnot(None), UFCFight.flag_b.isnot(None)))
        .order_by(UFCEvent.date.desc())
        .all()
    )
    found: dict[str, dict] = {}
    for fa, ia, la, ca, fb, ib, lb, cb in rows:
        for name, img, flag, country in ((fa, ia, la, ca), (fb, ib, lb, cb)):
            if not name:
                continue
            n = normalize_name(name)
            if n not in norms:
                continue
            d = found.setdefault(n, {"image_url": None, "flag_url": None, "country": None})
            # newest first, so the first non-null value per field wins
            if img and not d["image_url"]:
                d["image_url"] = img
            if flag and not d["flag_url"]:
                d["flag_url"], d["country"] = flag, country
    return found


def _event_images(db, norms: set[str]) -> dict[str, str]:
    """Just the event headshots — what the backfill needs to know it can skip."""
    return {n: d["image_url"] for n, d in _event_details(db, norms).items() if d["image_url"]}


def lookup(db, names: list[str]) -> dict[str, dict]:
    """Picture and flag for each name, keyed by normalize_name. Database reads
    only — safe on a request path. Every name gets an entry; image_url None
    means the UI should draw the placeholder, flag_url None means no flag."""
    norms = {normalize_name(n) for n in names}
    event = _event_details(db, norms)
    backfilled = {
        row.fighter_norm: row
        for row in db.query(FighterHeadshot).filter(FighterHeadshot.fighter_norm.in_(norms))
    }
    out = {}
    for n in norms:
        ev = event.get(n, {})
        # flags only ever come from event cards, whatever supplied the picture
        flag = {"flag_url": ev.get("flag_url"), "country": ev.get("country")}
        if ev.get("image_url"):
            out[n] = {"image_url": ev["image_url"], "source": "ufc", "credit": None, **flag}
        elif n in backfilled and backfilled[n].image_url:
            row = backfilled[n]
            credit = None
            if row.source == "commons":
                credit = {"author": row.credit_author, "license": row.credit_license, "url": row.credit_url}
            out[n] = {"image_url": row.image_url, "source": row.source, "credit": credit, **flag}
        else:
            out[n] = {"image_url": None, "source": None, "credit": None, **flag}
    return out


def backfill(db, names: list[str], delay: float = 1.0, retry_missing: bool = False) -> dict:
    """Fetch pictures for anyone who has neither an event headshot nor a
    backfilled row. Slow (network) — run from the script, never a request.

    `delay` spaces requests out so neither ufc.com nor Wikimedia sees a burst.
    `retry_missing` re-tries fighters previously recorded as "nothing found"
    (e.g. after a Wikipedia article gains a photo)."""
    norms = {normalize_name(n): n for n in names}
    has_event = _event_images(db, set(norms))
    rows = {r.fighter_norm: r for r in
            db.query(FighterHeadshot).filter(FighterHeadshot.fighter_norm.in_(list(norms)))}

    stats = {"ufc": 0, "commons": 0, "none": 0, "skipped": 0}
    for norm, name in norms.items():
        existing = rows.get(norm)
        if norm in has_event or (existing and (existing.image_url or not retry_missing)):
            stats["skipped"] += 1
            continue

        fields = {"image_url": None, "source": None, "credit_author": None,
                  "credit_license": None, "credit_url": None}
        ufc = fetch_ufc(name)
        time.sleep(delay)
        if ufc:
            fields.update(image_url=ufc, source="ufc")
        else:
            commons = fetch_commons(name)
            time.sleep(delay)
            if commons:
                fields.update(source="commons", **commons)

        row = existing or FighterHeadshot(fighter_norm=norm, fighter=name)
        for k, v in fields.items():
            setattr(row, k, v)
        db.add(row)
        db.commit()                      # per fighter, so a crash keeps progress
        stats[fields["source"] or "none"] += 1
        log.info("headshot %-28s -> %s", name, fields["source"] or "none")
    return stats
