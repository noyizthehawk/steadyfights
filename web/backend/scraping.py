"""Scraping + settling logic — everything that talks to ufc.com or mutates the
DB from scraped data. Kept out of the routers so the HTTP layer stays thin and
the CLI scripts (settle.py, refresh_data.py) can call these directly."""
import sys
import subprocess
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from . import PROJECT_ROOT
from .config import BASE, headers
from .models import UFCEvent, UFCFight
from part_2 import Prediction_model as model


def _norm_name(s):
    """Lowercase + strip accents so 'Jiří Procházka' matches 'Jiri Prochazka'."""
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def apply_event_details(event: UFCEvent, an_event: dict):
    """Copy the main event fields from scraped data onto the DB object."""
    event.title = an_event["title"]
    event.date = an_event["date"]
    event.venue = an_event["venue"]
    event.poster = an_event["poster"]


def apply_fight_odds(fight: UFCFight, scraped_fight: dict):
    """Copy the volatile odds fields from scraped data onto the DB object."""
    fight.odds_a = scraped_fight["odds_a"]
    fight.odds_b = scraped_fight["odds_b"]
    fight.img_a = scraped_fight["img_a"]
    fight.img_b = scraped_fight["img_b"]


def save_events(events: list, db: Session):
    """Upsert scraped events and their fights into the database."""
    #for an event in the list of events
    for an_event in events:
        event = db.query(UFCEvent).filter_by(event_link=an_event["event_link"]).first()
        #if that event doestn exist in the db we apply the event detail onto the db
        if event is None:
            event = UFCEvent(event_link=an_event["event_link"])
            db.add(event)

        apply_event_details(event, an_event) #apply event details

        existing_fights = {f.matchup: f for f in event.fights}

        for scraped_fight in an_event["fights"]:
            fight_record = existing_fights.get(scraped_fight["matchup"])
            if fight_record is None:
                fight_record = UFCFight(
                    matchup=scraped_fight["matchup"],
                    fighter_a=scraped_fight["fighter_a"],
                    fighter_b=scraped_fight["fighter_b"],
                )
                event.fights.append(fight_record)
            apply_fight_odds(fight_record, scraped_fight)

    db.commit()


def _clean_odds(text):
    text = text.strip()
    return text if text not in ("", "-") else None


def render_html(url, wait_selector=None):
    """ fetching the winners with a headless browser. regualr bautifulsoup can get html that is Jvascript rendered and not visible to the user so
    we need to render the html with a headless browser. """
    from playwright.sync_api import sync_playwright  # lazy: only settling needs it
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=headers["User-Agent"])
        try:
            # domcontentloaded, not networkidle: ufc.com's ads/polling keep the
            # network busy so networkidle never fires. The selector wait below is
            # the real "JS finished injecting results" signal.
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=15000)
                except Exception:
                    pass  # card may not be scored yet — return what's loaded
            return page.content()
        finally:
            browser.close()


def scrape_winners(event_url):
    """scrape winners calls render html to get the page then parse it with bs4"""
    # render first: the win/loss markers are injected by JS, absent from static HTML
    html = render_html(BASE + event_url, wait_selector=".c-listing-fight__outcome--win")
    soup = BeautifulSoup(html, "html.parser")

    list_of_winners = []
    for bout in soup.select(".c-listing-fight"):
        names = [n.get_text(" ", strip=True) for n in bout.select(".c-listing-fight__corner-name")]
        if len(names) < 2:
            continue  # skip incomplete blocks

        fighter_a, fighter_b = names[0], names[1]

        # pull outcomes — .c-listing-fight__outcome-wrapper, one per corner
        wrappers = bout.select(".c-listing-fight__outcome-wrapper")
        if len(wrappers) < 2:
            continue   # not scored yet → leave unsettled

        a_won = wrappers[0].select_one(".c-listing-fight__outcome--win") is not None
        b_won = wrappers[1].select_one(".c-listing-fight__outcome--win") is not None

        if a_won:
            winner = fighter_a
        elif b_won:
            winner = fighter_b
        else:
            winner = None
        list_of_winners.append({
            "matchup": f"{fighter_a} vs {fighter_b}",
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "winner": winner
        })

    return list_of_winners


def settle_event(db, event):
    # match in db and get winner
    winners = scrape_winners(event.event_link) #get he winnser from the playwrigtht scrape
    results = {w["matchup"]: w["winner"] for w in winners}
    settled = 0
    for fight in event.fights:
        winner = results.get(fight.matchup)
        if winner and fight.winner is None:
            fight.winner = winner
            settled += 1
    db.commit()

    return settled


def run_settle(db) -> dict:
    """Settle every finished event that still has an unsettled fight.
    Plain function so both the HTTP route and the CLI cron script can call it."""
    now = int(time.time())
    events = (
        db.query(UFCEvent)
        .filter(UFCEvent.date < now)
        .filter(UFCEvent.fights.any(UFCFight.winner.is_(None)))
        .all()
    )
    total = 0
    for event in events:
        total += settle_event(db, event)
        time.sleep(1)
    return {"events": len(events), "settled": total}


def scrape_event_details(event_url):
    #visit individual event
    res = requests.get(BASE + event_url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    #poster  .c-hero__image is a wrapper div; the real event art is the <img> inside it
    poster_img = soup.select_one(".c-hero__image img")
    poster = poster_img["src"] if poster_img and poster_img.has_attr("src") else None

    fights = []
    for bout in soup.select(".c-listing-fight"):
        names = [n.get_text(" ", strip=True) for n in bout.select(".c-listing-fight__corner-name")] #get names
        odds = [o.get_text(strip=True) for o in bout.select(".c-listing-fight__odds-amount")] # get odds
        if len(names) < 2:
            continue  # skip incomplete blocks

        fighter_a, fighter_b = names[0], names[1]
        odds_a = _clean_odds(odds[0]) if len(odds) >= 2 else None
        odds_b = _clean_odds(odds[1]) if len(odds) >= 2 else None

        # fighter headshots — scoped to the red/blue corner so we skip the flag imgs
        img_a_el = bout.select_one(".c-listing-fight__corner-image--red img")
        img_b_el = bout.select_one(".c-listing-fight__corner-image--blue img")
        img_a = img_a_el["src"] if img_a_el and img_a_el.has_attr("src") else None
        img_b = img_b_el["src"] if img_b_el and img_b_el.has_attr("src") else None

        fights.append({
            "matchup": f"{fighter_a} vs {fighter_b}",
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "odds_a": odds_a,
            "odds_b": odds_b,
            "img_a": img_a,
            "img_b": img_b,
        })

    return poster, fights


def scrape_events():
    html_data = requests.get(BASE + "/events", headers=headers, timeout=10).text
    soup = BeautifulSoup(html_data, "html.parser")

    results = []
    for event in soup.find_all("div", class_="l-listing__item"):
        article = event.find("article", class_="c-card-event--result")
        if not article:
            continue
        #headline and other improtant stuff
        headline = article.find("h3", class_="c-card-event--result__headline")
        title = headline.find("a").text.strip() if headline else None
        event_link = headline.find("a")["href"] if headline else None

        #date
        date_div = article.find("div", class_="c-card-event--result__date")
        timestamp = date_div.get("data-main-card-timestamp") if date_div else None
        if timestamp and int(timestamp) < time.time():
            continue
         # Venue
        location = article.find("div", class_="c-card-event--result__location")
        venue = location.find("h5").text.strip() if location else None

        # The bouts (names + odds) come from the event's detail page, where
        poster, fights = scrape_event_details(event_link) if event_link else (None, []) # get event details and fights 
        time.sleep(1)
        results.append({
            "title": title,
            "event_link": event_link,
            "date": timestamp,
            "venue": venue,
            "poster": poster,
            "fights": fights,
        })
    return results


def scrape_and_save(db: Session):
    results = scrape_events()
    save_events(results, db)
    return results


def _run_refresh(no_scrape: bool) -> None:
    """Background task to run a full data refresh + model retrain."""
    cmd = [sys.executable, str(PROJECT_ROOT / "refresh_data.py")]
    if no_scrape:
        cmd.append("--no-scrape")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    model.train()
