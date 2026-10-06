"""Generate career summaries for fighters."""
import json
import logging
import anthropic

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from redis import RedisError

from .config import ANTHROPIC_API_KEY
from .redis_client import redis_client
from .models import FighterBio
from part_2.career import career_summary_api, normalize_name

log = logging.getLogger(__name__)

MODEL = "claude-opus-5"

# Ceiling on how many bios may be WRITTEN in a day, across everyone.
#
# Not a per-user or per-IP limit: those cap behaviour, and the thing worth
# capping here is spend. The endpoint is public and the cache key is the
# fighter, so walking 2,766 names generates 2,766 times — about $36. Bounded,
# since each fighter is only ever written once, but $36 at a stranger's
# choosing. A global counter bounds it regardless of who asks or from where.
#
# 60/day covers a card settling (~12 fighters) several times over, and fills
# the back catalogue in under three months of ordinary browsing.
DAILY_GENERATION_CAP = 60


def _generation_budget_left() -> bool:
    """False once today's cap is spent. Fails OPEN when Redis is unavailable.

    Failing open on a spend control is normally wrong, but the total exposure
    here is a one-time ~$36 and the alternative is every profile losing its
    rundown whenever the cache is down.
    """
    if redis_client is None:
        return True
    try:
        from datetime import date
        key = f"biogen:{date.today().isoformat()}"
        used = redis_client.incr(key)
        if used == 1:
            redis_client.expire(key, 172800)   # 2 days, so the key self-clears
        return used <= DAILY_GENERATION_CAP
    except RedisError:
        return True

# Built lazily, like the Gemini client: the app must still boot on a box with
# no key, since only this one endpoint needs it.
_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def is_configured() -> bool:
    return bool(ANTHROPIC_API_KEY)

_PROMPT = """You write the career rundown that sits on a fighter's profile page.

You are given one fighter's complete record as JSON. Write 3 short paragraphs,
around 150-190 words, in plain prose. No headings, no bullet points, no markdown.

VOICE
Write like someone who watches the sport talking to someone who also watches it.
Direct, a bit conversational, confident about what the numbers show. Contractions
are fine. Short sentences are fine.

What that does NOT mean: no hype, no cliches ("make no mistake", "the numbers
don't lie", "one thing is certain"), no rhetorical questions, no addressing the
reader, no sign-off line. If a sentence could appear on any fighter's page, cut
it — every sentence has to be about THIS record.

WHAT TO COVER
1. What the career adds up to, and the shape of it.
2. How they fight and who they have fought. Spend most of your words here.
3. Where they are right now.

THE METRICS — be specific about these, they are the point of the page
Do not just name a figure as high or low. Say what it means in the cage:
- avg_adj_perf / recent_perf (0-100): how well they perform once the quality of
  the opponent is accounted for. High means they look good against anyone.
- avg_opp_strength / recent_opp_strength (0-100): the calibre they have been
  matched against. A gap between the career and recent figures is a story —
  climbing the division, or being matched softly.
- volatility: how much they swing fight to fight. Low means you know what you
  are getting; high means they can look unbeatable one night and ordinary the
  next. Say which.
- phases (early/mid/late): adj_perf is out of 75, opp_strength is a 0-1 ratio.
  Compare the phases to each other, not to an absolute.
- tale_of_the_tape: translate the rates, and mind the UNITS, which are not all
  the same:
    slpm, sapm     significant strikes landed / absorbed PER MINUTE
    td_avg         takedowns PER 15 MINUTES, i.e. per three rounds, so divide
                   by three before saying anything "per round"
    sub_avg        submission attempts PER 15 MINUTES, same division applies
    str_acc, str_def, td_acc, td_def   percentages
  High td_avg with high sub_avg is a grappler hunting finishes; high slpm with
  low sapm is someone who hits without getting hit.

RULES — these outrank everything above
- Use ONLY what is in the JSON. You may well recognise this fighter; what you
  remember about them is not evidence and must not reach the page. No opponent,
  event, date, title, nickname, country, division or technique that is not
  written there. The division IS given — use that field, never your own memory.
- Superlatives ("best", "worst", "toughest", "highest") are claims about a
  comparison. Check every value before writing one, and do not assume the
  figures move together. A phase can hold the best performance and the toughest
  opposition while a different phase has the better win rate; listing all three
  as if they belong to one phase is wrong even when two of them are right.
- No dashes of any kind in the prose: no em dashes, no en dashes, no hyphens
  joining clauses. Write two sentences, or use a comma. Hyphens inside a word
  that is normally spelled with one are fine (first-round, top-tier).
- Never claim a streak, run or sequence unless the records prove it. "3 - 2" is
  not a run. aged_well is sorted by how much an opponent improved afterwards,
  NOT by date, so it cannot tell you what happened most recently.
- Do not restate raw numbers the page already shows beside your text. Say what
  they mean instead.
- Past tense for a retired or inactive fighter.
- No predictions about future fights.

record and recent_record are "wins - losses". career_score, avg_adj_perf,
recent_perf, avg_opp_strength and recent_opp_strength are all 0-100, where 50
is roughly the roster median."""


def _payload(summary: dict) -> str:
    """The summary as the model sees it.

    The timeline goes: it is one row per fight and the longest part of the blob,
    and the phase aggregates already say what it would say. Everything else is
    passed through — at this volume there is no reason to be stingy, and the
    model writing from fewer facts is the failure mode that matters.
    """
    trimmed = {k: v for k, v in summary.items() if k != "timeline"}
    return json.dumps(trimmed, default=str)


def generate(summary: dict) -> str:
    """Call the model. Raises on failure — the caller decides what that means.

    effort "low" because this is short, fully-specified writing with every fact
    supplied. Thinking is on by default on this model and there is nothing here
    worth thinking hard about.
    """
    resp = _anthropic().messages.create(
        model=MODEL,
        max_tokens=1024,                      # the brief asks for 150-190 words
        system=_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": _payload(summary)}],
    )
    # Join rather than take the first: content is a list of blocks, a thinking
    # block can precede the text, and long output can arrive split across
    # several text blocks.
    return "".join(b.text for b in resp.content if b.type == "text").strip()



def get_or_create(db, fighter: str, *, force: bool = False) -> dict:
    """Cached bio for `fighter`, generating only when the record has changed.
    Returns {"body", "cached", "fights"} or {"body": None, "reason": ...}.
    """
    summary = career_summary_api(fighter)
    if summary is None:
        return {"body": None, "reason": "fighter not found"}

    norm = normalize_name(fighter)
    fights = int(summary["total_fights"])
    row = db.execute(
        select(FighterBio).where(FighterBio.fighter_norm == norm)
    ).scalar_one_or_none()

    # The fight count IS the cache key: same count, same facts, same text.
    if row is not None and row.fights_at_generation == fights and not force:
        return {"body": row.body, "cached": True, "fights": fights}

    if not is_configured():
        # Stale text beats no text — a bio written one fight ago is still
        # mostly true, where an empty section is just broken.
        if row is not None:
            return {"body": row.body, "cached": True, "stale": True, "fights": fights}
        return {"body": None, "reason": "ANTHROPIC_API_KEY not configured"}

    if not _generation_budget_left():
        log.warning("daily bio generation cap (%d) reached", DAILY_GENERATION_CAP)
        if row is not None:
            return {"body": row.body, "cached": True, "stale": True, "fights": fights}
        return {"body": None, "reason": "daily generation limit reached"}

    try:
        body = generate(summary)
    except Exception as e:
        # The SDK already retried 429/5xx twice before raising, so anything
        # landing here has survived backoff.
        status = getattr(e, "status_code", None)
        detail = {
            401: "anthropic api key rejected",
            429: "anthropic rate limit (retried and still failed)",
            529: "anthropic overloaded (transient, retried and still failed)",
        }.get(status, f"{type(e).__name__}" + (f" {status}" if status else ""))
        log.warning("bio generation failed for %s: %s", fighter, detail)
        if row is not None:
            return {"body": row.body, "cached": True, "stale": True, "fights": fights}
        return {"body": None, "reason": detail}

    if not body:
        return {"body": None, "reason": "model returned nothing"}

    if row is None:
        row = FighterBio(fighter_norm=norm, fighter=summary["fighter"])
        db.add(row)
    row.fighter = summary["fighter"]
    row.body = body
    row.fights_at_generation = fights
    row.model = MODEL
    try:
        db.commit()
    except IntegrityError:
        # Two requests for the same fighter raced: both read no row, both spent
        # ~15s generating, and uq fighter_norm rejected the second INSERT. The
        # loser's text is just as valid, but the winner's is already stored and
        # a reader seeing a different bio on refresh would be worse than losing
        # this one. Keep what is in the table.
        db.rollback()
        row = db.execute(
            select(FighterBio).where(FighterBio.fighter_norm == norm)
        ).scalar_one_or_none()
        if row is not None:
            return {"body": row.body, "cached": True, "fights": row.fights_at_generation}
        raise
    return {"body": body, "cached": False, "fights": fights}
