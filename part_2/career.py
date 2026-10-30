
"""
Career analysis for the web API.
"""
import math
import os
import re
from functools import lru_cache

import numpy as np
import pandas as pd
from unidecode import unidecode

from part_2.career_score import compute_career_score, soft_cap
from part_2.elo import add_elo


def normalize_name(s):
    # Transliterate to ASCII + lowercase so names match across sources.
    # unidecode (not just accent stripping) handles ł/ø/đ, which don't decompose
    # into base+accent: 'Jan Błachowicz' -> 'jan blachowicz', 'Rakić' -> 'rakic'.
    return " ".join(unidecode(str(s)).lower().split())

script_dir = os.path.dirname(os.path.abspath(__file__))
career_csv = os.path.join(script_dir, "../csv/fighter_opponent_strength_extra.csv")
fighter_csv = os.path.join(script_dir, "../csv/fighter_level_data.csv")

# Loaded once on first use and cached afterwards (so that
# a data refresh restarts the process, which re-reads them).
_career_df = None


def _load():
    """Load and cache """
    global _career_df
    if _career_df is not None:
        return _career_df

    career = pd.read_csv(career_csv)
    # compute_career_score needs title_fight + division, which live in the
    # fighter-level data. Join on fighter name and fight number 
    extra = (
        pd.read_csv(fighter_csv)[["name", "fight_number", "title_fight", "division", "date",
                                  "method", "finish_round"]]
        .drop_duplicates(subset=["name", "fight_number"])
    )
    career = career.merge(
        extra,
        left_on=["Fighter", "fight_number"],
        right_on=["name", "fight_number"],
        how="left",
    )
    # parse once here: the aged-well index compares these against title-fight
    # dates, and a str vs Timestamp comparison raises rather than silently
    # misbehaving
    career["date"] = pd.to_datetime(career["date"], errors="coerce")
    # precompute a normalized name column once so lookups can match accent-free
    career["Fighter_norm"] = career["Fighter"].map(normalize_name)
    _career_df = career
    return career


# Recent windows. Form (performance + W-L) reacts fast, so it reads the last 3;
# strength of recent opposition needs more opponents to mean anything, so it
# keeps 5. Trajectory (last 5 vs everything before) is a separate test and
# doesn't use either.
RECENT_FORM_FIGHTS = 3
RECENT_OPP_FIGHTS = 5


def _recent_form(fights):
    """Recency-weighted Adj Perf over the last RECENT_FORM_FIGHTS fights (rows
    sorted oldest first): the latest counts 3x, the one before 2x, the oldest 1x.
    A plain mean let one outlier night outweigh a fresh loss — Chimaev read
    99.8 straight after losing to Strickland, carried by the Du Plessis
    performance two fights back. Weighted, he's still elite but visibly dented.
    Returns the raw value; callers scale it like any other Adj Perf average.

    A fight with no Adj Perf is skipped rather than blanking the whole figure:
    38 fighters had one in their last 3, which left their form empty."""
    recent = fights["Adj Perf"].dropna().tail(RECENT_FORM_FIGHTS).to_numpy(dtype=float)
    if len(recent) == 0:
        return float("nan")
    weights = np.arange(1, len(recent) + 1)
    return float((recent * weights).sum() / weights.sum())


_QUANTILES = {
    "adj": (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90),
    "vol": (0.25, 0.50, 0.75, 0.90),
    # Bell-shaped
    "opp": (0.03, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90, 0.97),
    "opp_recent": (0.03, 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90, 0.97),

}

_thresholds = None


def _get_thresholds():
    global _thresholds
    if _thresholds is not None:
        return _thresholds
    df = _load()
    g = df.groupby("Fighter")
    series = {
        "adj": g["Adj Perf"].mean(),
        "vol": g["Raw Perf"].std().dropna(), 
        "opp": g["Opp Str"].mean(),
        "opp_recent": g["Opp Str"].apply(lambda x: x.tail(RECENT_OPP_FIGHTS).mean()).dropna(),
    }
    _thresholds = {
        key: [s.quantile(q) for q in _QUANTILES[key]]
        for key, s in series.items()
    }
    return _thresholds


def _threshold(key, q):
    """One cut point, looked up BY QUANTILE rather than by position.

    Positional indexing broke the moment the quantile list changed length —
    ["vol"][1] meant p75 with three edges and p50 with four, silently moving a
    behavioural threshold. Ask for the quantile you actually mean.
    """
    return _get_thresholds()[key][_QUANTILES[key].index(q)]


def _bucket(value, edges, labels):
    """Map value to a label. `labels` has len(edges)+1 entries, low band first.

    The length check is not paranoia — it is the bug this function already had.
    zip() stops at the shorter sequence, so adding quantiles to _QUANTILES
    without adding labels silently truncated the ladder: everything above the
    last paired edge fell through to labels[-1], and 60% of all fighters were
    reported as "Elite Performances". Nothing errored. Fail loudly instead.
    """
    if len(labels) != len(edges) + 1:
        raise ValueError(
            f"_bucket needs len(labels) == len(edges)+1, "
            f"got {len(labels)} labels for {len(edges)} edges"
        )
    if value is None or pd.isna(value):
        return "Not enough data"
    for edge, label in zip(edges, labels):
        if value < edge:
            return label
    return labels[-1]


# How the trajectory line is phrased. Present tense is a lie for someone who
# last fought in 2017 — "on a tear right now" about GSP reads as broken data.
# Each bucket carries an active and a past-tense form.
# When the last-5 vs earlier gap ISN'T bigger than the fighter's own noise,
# there is no trend to report — so describe the level they sustained instead.
# Khabib retired 29-0 with a +3.5 delta against a standard error of 3.7: calling
# that "leveling up" invents a rise and misses that he was simply elite.
_LEVEL = {
    "elite":   ("Elite the whole way, sustained at the very top",
                "Was elite the whole way, sustained at the very top"),
    "high":    ("A consistent high-level competitor",
                "Was a consistent high-level competitor"),
    "solid":   ("Steady and dependable across the run",
                "Steady and dependable across the run"),
    "scrappy": ("Fought to a mixed record without finding a groove",
                "Fought to a mixed record without finding a groove"),
}

# "No trend" has two very different causes, and they need opposite words.
# A small delta from a steady fighter means genuinely consistent. A small
# t-statistic from a WILD fighter means the noise swamped any signal —
# McGregor's SE is 14.7 because his fights range from 2 to 83, so calling him
# "consistent" would assert the exact opposite of what the test found.
_LEVEL_ERRATIC = {
    "elite":   ("Elite on his night, but wildly up and down",
                "Elite on his night, but wildly up and down"),
    "high":    ("Hot and cold, capable of anything on the night",
                "Was hot and cold, capable of anything on the night"),
    "solid":   ("Streaky, hard to call from one fight to the next",
                "Streaky, hard to call from one fight to the next"),
    "scrappy": ("Never strung a run together",
                "Never strung a run together"),
}

# how many standard errors the gap must clear before it counts as a trend
_TREND_T = 1.5

_TRAJECTORY = {
    "rising": (
        "On a tear right now, getting better the harder the fights get",
        "Was on the rise, getting better as the fights got harder",
    ),
    "improving": (
        "Leveling up, holding their own as the competition gets stiffer",                         
        "Was leveling up, holding their own as the competition got stiffer",
    ),
    "steady": (
        "Holding it down, grinding against top competition consistently",
        "Held it down, grinding against top competition consistently",
    ),
    "declining": (
        "Deep in the trenches right now.",
        "Was deep in the trenches by the end man",
    ),
}


_level_pop = None


def _level_percentile(avg_adj):
    """Where a career average sits among all fighters with 3+ fights."""
    global _level_pop
    if _level_pop is None:
        df = _load()
        per = df.groupby("Fighter")["Adj Perf"].mean()
        counts = df.groupby("Fighter").size()
        _level_pop = np.sort(per[counts >= 3].dropna().values)
    if len(_level_pop) == 0:
        return 50.0
    return float(np.searchsorted(_level_pop, avg_adj) / len(_level_pop) * 100)


def _activity(last_fight, now=None):
    """active / inactive / retired, from time since the last bout.

    """
    if pd.isna(last_fight):
        return {"status": "unknown", "last_fight": None, "years_since": None}
    now = now or pd.Timestamp.now()
    years = (now - last_fight).days / 365.25
    status = "active" if years < 1.5 else ("inactive" if years < 3.0 else "retired")
    return {
        "status": status,
        "last_fight": str(last_fight)[:10],
        "years_since": round(years, 1),
    }


# Ten bands, one per decile. Each label has to be distinguishable from its
# neighbours at a glance, so the ladder climbs through plain words rather than
# stacking adverbs ("fairly solid", "very solid") that read as the same rung.
_PERF_LABELS = [
    "Outmatched", "Developing", "Raw", "Competitive", "Capable",
    "Solid", "Proven", "Strong", "Standout", "Elite",
]


# Label bands are bands of the DISPLAYED number, in tens.
#
# The number was a min-max position on a fixed range while the label was a
# quantile rank against other fighters — two different transforms, so they
# drifted apart and a displayed 60 could carry a label earned by a far higher
# value ("Elite Opposition" at 60). Bucketing the scaled figure means the label
# reads straight off the number and the two can never disagree.
_DISPLAY_BANDS = (10, 20, 30, 40, 50, 60, 70, 80, 90)


def _perf_label(scaled):
    """`scaled` is the 0-100 figure shown on the page, not the raw average."""
    return _bucket(scaled, _DISPLAY_BANDS, _PERF_LABELS)


def _volatility_label(vol):
    # lower volatility = steadier, the lower the better
    return _bucket(vol, _get_thresholds()["vol"],
                   ["Very consistent performances", "Consistent Performances", "Fairly steady",
                    "Streaky", "Unpredictable performances"])


def _opp_label(scaled):
    """`scaled` is the 0-100 figure shown on the page, not the raw average.

    One set of bands for both the career and last-5 figures: they are shown on
    the same scale, so the same number has to mean the same thing in both.
    """
    return _bucket(scaled, _DISPLAY_BANDS,
                   ["Cherry-Picked Opposition", "Padded Opposition", "Protected Opposition",
                    "Soft Opposition", "Average Opposition", "Respectable Opposition",
                    "Tough Opposition", "Contender-Level Opposition", "Elite Opposition",
                    "Murderers' Row"])


# Observed min/max of per-fighter career AVERAGES (fighters with >=3 fights),
# used to min-max normalize each stat onto 0-100 for display: the weakest career
# average maps to ~0, the strongest to ~100.
_SCALE_BOUNDS = {
    "raw_perf": (30.0, 70.0),
    "adj_perf": (3.0, 65.0),
    "opp_str":  (0.42, 0.63),
    # A 5-fight mean swings wider than a career mean, so it needs its own upper
    # bound or it clamps: observed last-5 range is 0.422-0.688 against a career
    # range of 0.422-0.626.
    "opp_str_recent": (0.42, 0.69),
    # ONE opponent (the career chart's dots) ranges 0.39-0.75, far past a career
    # average, so it gets its own bounds; see _fight_opp for how it's blended
    # with Elo.
    "opp_str_fight": (0.41, 0.67),
    # opponent Elo on fight night: ~1460 is a debutant who has lost, ~1700 an
    # established champion (the 99th percentile is 1652, the max 1761)
    "opp_elo": (1460.0, 1700.0),
}


# Aged well: how far an opponent's rating must climb after the fight to count
# as a story. 15 rating points ≈ the 0.05 of raw strength it used to be.
AGED_WELL_MIN_GAIN = 15.0

_opp_elo = None


def _opp_elo_lookup():
    """(fighter_norm, date) -> the opponent's Elo going into that fight, from
    part_2.elo: the same ratings Bout Brain trains on. Built once."""
    global _opp_elo
    if _opp_elo is None:
        fl = pd.read_csv(fighter_csv, usecols=["fight_id", "name", "winner", "date"], low_memory=False)
        fl["date"] = pd.to_datetime(fl["date"], errors="coerce")
        fl = fl.sort_values("date").reset_index(drop=True)   # Elo replays in date order
        add_elo(fl)
        _opp_elo = dict(zip(zip(fl["name"].map(normalize_name), fl["date"]),
                            fl["opponent_elo_before_fight"]))
    return _opp_elo


def _fight_opp(opp_str, fighter_norm, date):
    """How strong one opponent was on fight night, 0-99: the average of two
    measures whose mistakes run in opposite directions.

    * Opp Str (their record and performance so far) can't see WHO they beat,
      so an unbeaten record against modest opposition rates elite: Bryce
      Mitchell, 15-0, read 98 against Topuria, above Holloway at 80.
    * Elo knows who they beat but starts every UFC newcomer at 1500, so a
      champion from another promotion reads as a nobody: Cormier 69, Gane 65.

    Blended, Mitchell reads 77 and Holloway 88, while Cormier and Gane stay
    in the 80s. 90+ falls from 5.2% of fights to 0.5%: Usman, Volkanovski,
    Du Plessis. Without an Elo for the fight it falls back to Opp Str alone."""
    by_record = _scale_to_100(opp_str, "opp_str_fight")
    elo = _opp_elo_lookup().get((fighter_norm, date))
    if elo is None or pd.isna(elo):
        return by_record
    return round((by_record + _scale_to_100(elo, "opp_elo")) / 2, 1)


def _scale_to_100(value, kind):
    """Min-max normalize a stat onto 0-100: floored at 0, eased toward 100 at
    the top by soft_cap (shared with the career score) instead of clamped."""
    lo, hi = _SCALE_BOUNDS[kind]
    scaled = (value - lo) / (hi - lo) * 100
    return round(float(soft_cap(max(0.0, scaled))), 1)


def _compute_career_score(fights, max_adj_perf):
    """Thin adapter over the shared scorer, passing career.py's column names."""
    return compute_career_score(
        fights, max_adj_perf,
        win_col="win(1)/loss(0)", perf_col="Adj Perf",
    )


_METHOD_SHORT = [
    ("doctor", "TKO"), ("could not continue", "TKO"),
    ("tko", "TKO"), ("ko", "KO"),
    ("sub", "SUB"),
    ("u-dec", "UD"), ("unanimous", "UD"),
    ("s-dec", "SD"), ("split", "SD"),
    ("m-dec", "MD"), ("majority", "MD"),
    ("draw", "DRAW"), ("overturned", "NC"), ("no contest", "NC"), ("dq", "DQ"),
]


def _short_method(method, finish_round):
    """ 'Decision - Unanimous' -> 'UD';  'KO/TKO' in round 2 -> 'KO R2'.

    The raw column carries 40-odd spellings of a dozen outcomes, several of
    them per-technique ('SUB Rear Naked Choke'), which is far too long to sit
    in a list row. Matching is ordered and on a substring, since 'KO/TKO' holds
    both 'ko' and 'tko' and the more specific one has to win.
    """
    if pd.isna(method):
        return None
    text = str(method).lower()
    short = next((code for needle, code in _METHOD_SHORT if needle in text), None)
    if short is None:
        return None
    # A decision has no meaningful round; a finish does.
    if short in {"KO", "TKO", "SUB"} and pd.notna(finish_round):
        try:
            return f"{short} R{int(finish_round)}"
        except (TypeError, ValueError):
            pass
    return short


def _phase(sub):
    """Aggregate one career phase (early/mid/late), or None if it has no fights."""
    if sub.empty:
        return None
    # Per-fight log for this phase — drives the drill-down when a user clicks the tile.
    # Chronological here; the profile card orders it for display (newest first).
    bouts = [
        {
            "fight_number": int(r["fight_number"]),
            "opponent": r["opponent_name"],
            "won": bool(int(r["win(1)/loss(0)"])),
            "event": r["Event"],
            "date": str(r["date"])[:10] if pd.notna(r.get("date")) else None,
            "method": _short_method(r.get("method"), r.get("finish_round")),
            "adj_perf": round(float(r["Adj Perf"]), 1),
        }
        for _, r in sub.sort_values("fight_number").iterrows()
    ]
    return {
        "fights": int(len(sub)),
        "win_rate": round(float(sub["win(1)/loss(0)"].mean()) * 100, 1),
        # the same 0-100 ratings as the PERF and OPP rings, on the SAME bounds
        # so a phase and the career figure add up (the bars used to be raw
        # averages drawn out of 75). Wider bounds were tried and dropped: every
        # phase then read below the career ring.
        "perf": _scale_to_100(float(sub["Adj Perf"].mean()), "adj_perf"),
        "opp": _scale_to_100(float(sub["Opp Str"].mean()), "opp_str"),
        "bouts": bouts,
    }
_aged_well_index = None


def _aged_index():
    """Two lookups behind the 'aged well' view, built once and cached.

    opp_history — every rating each fighter ever recorded AS an opponent,
    date-sorted. The max of the ratings AFTER a given fight is what they went
    on to become. Each is _fight_opp, the same 0-99 Opp Str + Elo blend as the
    career chart's dots, so "then" here and the chart's dot always agree.

    title_wins — every date each fighter won a title fight, sorted. A peak alone
    can't tell you someone became champion; Opp Str blends win rate and
    performance and knows nothing about belts.
    """
    global _aged_well_index
    if _aged_well_index is not None:
        return _aged_well_index

    df = _load()
    rows = df[["opponent_name", "date", "Opp Str", "Fighter_norm"]].dropna().copy()
    rows["rating"] = [_fight_opp(s, f, d) for s, f, d in
                      zip(rows["Opp Str"], rows["Fighter_norm"], rows["date"])]
    history = {}
    for name, g in rows.groupby("opponent_name"):
        g = g.sort_values("date")
        history[name] = (g["date"].tolist(), g["rating"].tolist())

    fl = pd.read_csv(fighter_csv, low_memory=False)
    tf = fl[(fl["title_fight"] == 1) & (fl["winner"] == fl["name"])].copy()
    tf["date"] = pd.to_datetime(tf["date"], errors="coerce")
    # EVERY title win, not just the first. Gaethje won an interim belt before
    # losing to Khabib and two more afterwards — taking the minimum said "already
    # champion" and hid that he went on to win again. The question is whether any
    # title came AFTER the fight, not when the earliest one was.
    title_wins = {n: sorted(g.dropna()) for n, g in tf.groupby("name")["date"]}

    _aged_well_index = (history, title_wins)
    return _aged_well_index


_fighter_level_df = None


def _fighter_level():
    """Load + cache the full fighter-level table. Unlike _load (which merges only
    a couple of columns), this keeps every column — including the UFCStats career
    aggregates (str_acc, td_def, reach, …)."""
    global _fighter_level_df
    if _fighter_level_df is None:
        df = pd.read_csv(fighter_csv)
        df["name_norm"] = df["name"].map(normalize_name)
        _fighter_level_df = df
    return _fighter_level_df


def _clean(x):
    """NaN -> None; round numbers; leave strings alone (JSON-safe)."""
    if pd.isna(x):
        return None
    if isinstance(x, (float, int, np.floating, np.integer)):
        return round(float(x), 2)
    return x


def get_fighter_stats(fighter):
    """Return a JSON-serializable career stats for one fighter or None if not found"""
    df = _fighter_level()
    rows = df[df["name_norm"] == normalize_name(fighter)]
    if rows.empty:
        return None
    # Some rows leave the aggregates blank (and the very last row can be dirty),
    # so prefer the most recent row that actually has them populated.
    good = rows[rows["str_acc"].notna()]
    row = (good if not good.empty else rows).sort_values("fight_number").iloc[-1]

    return {
        "str_acc":  _clean(row.get("str_acc")),     # significant strike accuracy %
        "str_def":  _clean(row.get("str_def")),     # significant strike defense %
        "td_acc":   _clean(row.get("td_avg_acc")),  # takedown accuracy %
        "td_def":   _clean(row.get("td_def")),      # takedown defense %
        "slpm":     _clean(row.get("splm")),        # sig. strikes landed / min
        "sapm":     _clean(row.get("sapm")),        # sig. strikes absorbed / min
        "td_avg":   _clean(row.get("td_avg")),      # takedowns / 15 min
        "sub_avg":  _clean(row.get("sub_avg")),     # submission attempts / 15 min
        "height_cm": _clean(row.get("height")),
        "reach_cm":  _clean(row.get("reach")),
        "stance":   (str(row.get("stance")).title() if not pd.isna(row.get("stance")) else None),
    }




# Tale-of-the-tape stats and which way is good. Raw values can't be compared
# across stats — a typical takedown defence (~63%) dwarfs a typical striking
# accuracy (~45%) — so each is ranked against its OWN spread across the roster.
STAT_DIRECTION = {
    "str_acc": +1, "str_def": +1, "td_acc": +1, "td_def": +1,
    "slpm": +1,                 # strikes landed / min
    "sapm": -1,                 # strikes absorbed / min: closer to zero is better
    "td_avg": +1, "sub_avg": +1,
}


# get_fighter_stats key -> column in the fighter-level CSV
_STAT_COLUMNS = {"str_acc": "str_acc", "str_def": "str_def", "td_acc": "td_avg_acc",
                 "td_def": "td_def", "slpm": "splm", "sapm": "sapm",
                 "td_avg": "td_avg", "sub_avg": "sub_avg"}
STAT_PERCENTILE_MIN_FIGHTS = 5   # the roster a percentile is measured against


@lru_cache(maxsize=None)
def _stat_distribution():
    """Each stat's values across fighters with 5+ UFC fights, sorted.

    Percentiles exist for CHOOSING a card's best stat and for its "Top X%"
    label. The bar itself is drawn by the frontend on the profile's own scale
    (web/frontend/src/lib/statScale.ts) so colours match everywhere; that
    scale isn't fair for choosing (a typical absorbed rate already scores ~63
    on it, a typical accuracy ~47), percentiles are. Cached for the process."""
    df = _fighter_level()
    good = df[df["str_acc"].notna()].sort_values("fight_number")
    latest = good.groupby("name_norm").last()          # same row get_fighter_stats picks
    counts = _load().groupby("Fighter_norm").size()
    roster = latest[latest.index.isin(counts[counts >= STAT_PERCENTILE_MIN_FIGHTS].index)]
    return {key: np.sort(roster[col].dropna().to_numpy(dtype=float))
            for key, col in _STAT_COLUMNS.items()}


def stat_percentile(key, value):
    """Share of the roster (0-100) this value is BETTER than, flipped where
    lower is better. Ties count half, so a value shared by many fighters
    lands in the middle of them rather than at either end."""
    values = _stat_distribution()[key]
    if len(values) == 0:
        return 50.0
    below = np.searchsorted(values, value, side="left")
    at_or_below = np.searchsorted(values, value, side="right")
    worse = len(values) - at_or_below if STAT_DIRECTION[key] < 0 else below
    ties = at_or_below - below
    return float((worse + ties / 2) / len(values) * 100)


# ---------------------------------------------------------------------------
# Leaderboards: the Fighters page's fun lists ("in form", "the gauntlet", ...)
# ---------------------------------------------------------------------------
LEADERBOARD_SIZE = 20
LEADERBOARD_MIN_FIGHTS = 5        # same bar as the stat percentiles
LEADERBOARD_MIN_MINUTES = 30      # per-minute rates explode over a 90-second career
ACTIVE_DAYS = 730                 # "active" = fought in the 2 years before the newest data


def _pct_rank(series):
    """0-100 percentile of each value within its own pool (ties share a rank)."""
    return series.rank(pct=True, method="average") * 100


def _cm_to_ft(cm):
    inches = round(cm / 2.54)
    return f"{inches // 12}'{inches % 12}\""


@lru_cache(maxsize=None)
def leaderboards():
    """Every list, top LEADERBOARD_SIZE each, as plain dicts:

        {key: [{"fighter", "value", "display", "fill", "note"}, ...]}

    `fill` is the bar (0-100): the score itself for the 0-100 scores (so it
    matches the PERF/OPP/RF cells), otherwise the percentile within that
    list's eligible pool. `note` is the one line under the bar.

    Eligible = active (relative to the newest fight in the data, so a stale
    refresh can't empty the lists) and 5+ UFC fights. Cached for the process,
    like the rest of the module: the data only changes on restart."""
    career_df = _load().copy()
    career_df["date"] = pd.to_datetime(career_df["date"], errors="coerce")
    newest = career_df["date"].max()
    per_fighter = career_df.groupby("Fighter_norm").agg(n=("fight_number", "size"), last=("date", "max"))
    eligible = per_fighter[(per_fighter["n"] >= LEADERBOARD_MIN_FIGHTS)
                           & ((newest - per_fighter["last"]).dt.days <= ACTIVE_DAYS)].index

    out = {}

    # -- from the tag: recent form and the recent schedule (both 0-100) -------
    tags = []
    for norm in eligible:
        t = _fighter_tag_cached(norm)
        name = career_df.loc[career_df["Fighter_norm"] == norm, "Fighter"].iloc[-1]
        tags.append((name, t))
    # each list shows the W-L over its own window
    notes = {
        "in_form": lambda t: f"Last {RECENT_FORM_FIGHTS}: {t['recent_record']}",
        "gauntlet": lambda t: f"Last {RECENT_OPP_FIGHTS}: {t['opp_record']}",
    }
    for key, field in (("in_form", "recent_form"), ("gauntlet", "strength_iq")):
        ranked = sorted(tags, key=lambda nt: nt[1][field], reverse=True)[:LEADERBOARD_SIZE]
        out[key] = [{"fighter": name, "value": t[field], "display": f"{t[field]:.0f}",
                     "fill": t[field], "note": notes[key](t)}
                    for name, t in ranked]

    # -- from the per-fight table: clinch, leg kicks, height --------------------
    fl = _fighter_level()
    fl = fl[fl["name_norm"].isin(eligible)]
    g = fl.groupby("name_norm").agg(
        name=("name", "last"), mins=("fight_time_min", "sum"),
        clinch=("clinch_landed", "sum"), sig=("sig_str_landed", "sum"),
        leg_att=("leg_atmpted", "sum"), leg_landed=("leg_landed", "sum"))
    g = g[g["mins"] >= LEADERBOARD_MIN_MINUTES]

    # clinch: ranked on VOLUME (strikes landed per 15 min); the share of all
    # their strikes goes underneath, which is what says "this is how they fight"
    g["clinch15"] = g["clinch"] / g["mins"] * 15
    g["clinch_fill"] = _pct_rank(g["clinch15"])
    out["clinch"] = [{"fighter": r["name"], "value": round(r["clinch15"], 2),
                      "display": f"{r['clinch15']:.1f}", "fill": r["clinch_fill"],
                      "note": f"{r['clinch'] / r['sig'] * 100:.0f}% of their strikes" if r["sig"] else ""}
                     for _, r in g.nlargest(LEADERBOARD_SIZE, "clinch15").iterrows()]

    # leg kicks: THROWN per minute, as asked. UFCStats counts every strike to the
    # leg, which in practice is kicks — hence "leg strikes" in the label
    g["leg_pm"] = g["leg_att"] / g["mins"]
    g["leg_fill"] = _pct_rank(g["leg_pm"])
    out["leg_kicks"] = [{"fighter": r["name"], "value": round(r["leg_pm"], 2),
                         "display": f"{r['leg_pm']:.1f}", "fill": r["leg_fill"],
                         "note": f"{r['leg_landed'] / r['leg_att'] * 100:.0f}% land" if r["leg_att"] else ""}
                        for _, r in g.nlargest(LEADERBOARD_SIZE, "leg_pm").iterrows()]

    # height: the latest row's figure; reach breaks ties (lots of 6'4"s)
    body = (fl.sort_values("fight_number").groupby("name_norm")
              .agg(name=("name", "last"), height=("height", "last"), reach=("reach", "last"))
              .dropna(subset=["height"]))
    body["fill"] = _pct_rank(body["height"])
    tallest = body.sort_values(["height", "reach"], ascending=False).head(LEADERBOARD_SIZE)
    out["tallest"] = [{"fighter": r["name"], "value": float(r["height"]),
                       "display": f"{_cm_to_ft(r['height'])} · {r['height']:.0f} cm",
                       "fill": r["fill"],
                       "note": f"Reach {r['reach']:.0f} cm" if pd.notna(r["reach"]) else ""}
                      for _, r in tallest.iterrows()]

    # plain floats only (numpy types don't serialise) and a rounded fill
    for rows in out.values():
        for row in rows:
            row["value"] = float(row["value"])
            row["fill"] = round(float(row["fill"]), 1)
    return out


def _json_safe(obj):
    """Convert a JSON-unsafe object to a JSON-safe one
    no nans in the json dunb if not 500 erro. fighter slike kevin holland, 
    ben askren etc that have been finished without any stirkes thrown etc get giveen a nan which causes the error
    so we replace it with None
    """
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def career_summary_api(fighter):
    """Return n a JSON-serializable career rundown for one fighter or None if not found"""
    df = _load()
    # match on the normalized name so accented/scraped spellings resolve too
    fights = df[df["Fighter_norm"] == normalize_name(fighter)].sort_values("fight_number")
    if fights.empty:
        return None

    max_adj = df["Adj Perf"].max()

    # for the graph
    timeline = [
        {
            "fight_number": int(r["fight_number"]),
            "opponent": r["opponent_name"],
            "won": bool(int(r["win(1)/loss(0)"])),
            "event": r["Event"],
            # each fight on the same 0-100 rating as PERF and OPP (a standout
            # night can top out at 100); was raw perf "out of 75"
            "perf": _scale_to_100(float(r["Adj Perf"]), "adj_perf"),
            "opp": _fight_opp(float(r["Opp Str"]), r["Fighter_norm"], r["date"]),
        }
        for _, r in fights.iterrows()
        if pd.notna(r["Adj Perf"]) and pd.notna(r["Opp Str"])
    ]

    # "Aged well": what the opponent went on to become AFTER this fight.
    #
    # Only what came after. Taking their all-time peak conflates two opposite
    # stories — Usman beat Leon Edwards in 2015 before Edwards was anyone
    # (aged well), while Adesanya beat a 2019 Anderson Silva whose peak was
    # 2012 (caught him late). Both look identical on an all-time max.
    hist, title_wins = _aged_index()
    aged = []
    # One row per opponent, the EARLIEST meeting. Usman fought Leon Edwards three
    # times, but only the 2015 win carries any hindsight — by the rematches
    # Edwards was already champion and there was nothing left to not-know.
    # `fights` is sorted by fight_number, so first seen is first fought.
    seen_opponents = set()
    for _, r in fights.iterrows():
        opp_name, when = r["opponent_name"], r["date"]
        if pd.isna(when) or pd.isna(r["Opp Str"]):
            continue
        dates, vals = hist.get(opp_name, ([], []))
        later = [v for d, v in zip(dates, vals) if d > when]
        peak_after = max(later) if later else None

        
        later_titles = [t for t in title_wins.get(opp_name, []) if t > when]
        became_champ = bool(later_titles)
        title_date = later_titles[0] if later_titles else None

        then = _fight_opp(float(r["Opp Str"]), r["Fighter_norm"], when)   # = the chart's dot
        gain = (peak_after - then) if peak_after is not None else 0.0
        # a flat reading is usually the <3-fight placeholder (39% of rows), not a
        # verdict, so it must not qualify as a story
        if (gain > AGED_WELL_MIN_GAIN or became_champ) and opp_name not in seen_opponents:
            seen_opponents.add(opp_name)
            aged.append({
                "fight_number": int(r["fight_number"]),
                "opponent": opp_name,
                "won": bool(int(r["win(1)/loss(0)"])),
                "event": r["Event"],
                "then": round(then, 1),
                "peak_after": round(float(peak_after), 1) if peak_after is not None else None,
                "became_champion": became_champ,
                # None when it happened in this very fight, else years later
                "champion_years_later": (
                    round((title_date - when).days / 365.25, 1)
                    if became_champ and title_date > when else None
                ),
            })
    aged.sort(key=lambda a: (a["peak_after"] or 0) - a["then"], reverse=True)

    # Career-phase buckets — used for the `phases` breakdown in the response.
    early = fights[fights["fight_number"] <= 5]
    mid = fights[(fights["fight_number"] >= 6) & (fights["fight_number"] <= 10)]
    late = fights[fights["fight_number"] >= 11]

    # Trajectory is recent form that is last 5 fights against everything before them.
    # Need at least 6 fights so there's a baseline to compare the last 5 against.
    activity = _activity(fights["date"].max())
    # needed by the trajectory below as well as the career label further down
    score = _compute_career_score(fights, max_adj)

    if len(fights) <= 5:
        bucket = "developing"
        trajectory = "Developing career — not enough fights to assess trajectory"
    else:
        recent = fights.tail(5)          # most recent 5 fights (rows are sorted by fight_number)
        earlier = fights.iloc[:-5]       # everything before them
        improvement = recent["Adj Perf"].mean() - earlier["Adj Perf"].mean()

        # Standard error of the difference between the two means. A raw delta
        # can't tell a real shift from a fighter who simply swings a lot —
        # McGregor's -18.4 comes with an SE of 14.7, so five fights can't
        # establish it, while Silva's -16.8 against 7.5 clearly can.
        se = np.sqrt(
            recent["Adj Perf"].var(ddof=1) / len(recent)
            + earlier["Adj Perf"].var(ddof=1) / max(1, len(earlier))
        )
        t_stat = improvement / se if se and not pd.isna(se) else 0.0

        if t_stat >= _TREND_T:
            bucket, table = ("rising" if improvement > 5 else "improving"), _TRAJECTORY
        elif t_stat <= -_TREND_T:
            bucket, table = "declining", _TRAJECTORY
        else:
            # no meaningful trend — say what level they held instead, and pick
            # the wording by whether they were actually steady or merely noisy.
            #
            # career_score, NOT an Adj Perf percentile. Adj Perf measures how well
            # you performed, not whether you won: Marvin Vettori is 9-9 with a
            # perfIQ of 75 — higher than Strickland's — and a percentile of 92,
            # so he read as "elite the whole way". career_score already folds in
            # win rate, opponent quality and title fights, and its cut points are
            # the ones career_label below is tuned on.
            bucket = ("elite" if score >= 90 else "high" if score >= 80
                      else "solid" if score >= 60 else "scrappy")
            spread = fights["Raw Perf"].std()
            # Compare the NUMBER, not the label. This used to test
            # _volatility_label(...) against display strings, so renaming one of
            # them silently reverted the fix and McGregor went back to being
            # called "consistent". edges are [p25, p75, p90]; p75 is where
            # streaky starts, which is the same cut the label uses.
            erratic = not pd.isna(spread) and float(spread) >= _threshold("vol", 0.75)
            table = _LEVEL_ERRATIC if erratic else _LEVEL

        # Past tense once they stop fighting — the read is still about their last
        # five bouts, but it describes where they were when they walked away
        # rather than claiming to know where they are now.
        present, past = table[bucket]
        if activity["status"] == "active":
            trajectory = present
        else:
            year = (activity["last_fight"] or "")[:4]
            prefix = "Retired" if activity["status"] == "retired" else "Inactive"
            trajectory = f"{prefix} since {year}. {past}." if year else past



    if score >= 90:
        label = "All-time dominant UFC career"
    elif score >= 80:
        label = "Elite championship career"
    elif score >= 70:
        label = "Sustained elite competitor at the top level"
    elif score >= 60:
        label = "High-level UFC contender career"
    else:
        label = "Inconsistent or developing UFC career"

    # Volatility is undefined for a single fight (std of one value); report 0 there.
    vol = fights["Raw Perf"].std()
    volatility = round(float(vol), 1) if pd.notna(vol) else 0.0

    avg_adj = float(fights["Adj Perf"].mean())
    avg_opp = float(fights["Opp Str"].mean())

    wins = fights[fights["win(1)/loss(0)"] == 1]
    losses = fights[fights["win(1)/loss(0)"] == 0]
    record = f"{len(wins)} - {len(losses)}"

    # Recent form: the last (up to) RECENT_FORM_FIGHTS fights, latest weighted
    # most (_recent_form), scored on the SAME 0-100 scale as avg_adj_perf so it's
    # directly comparable to the career number.
    # This captures "how good are they RIGHT NOW" — a fighter who improved late
    # (e.g. Oliveira) scores high here even if their career average is dragged
    # down by early years.
    recent = fights.tail(RECENT_FORM_FIGHTS)
    recent_perf = _scale_to_100(_recent_form(fights), "adj_perf")
    recent_wins = int((recent["win(1)/loss(0)"] == 1).sum())
    recent_record = f"{recent_wins} - {len(recent) - recent_wins}"

    recent_opp = float(fights.tail(RECENT_OPP_FIGHTS)["Opp Str"].mean())

    fighter_stats = get_fighter_stats(fighter)
    division = _division(fights)

    payload = {
        "fighter": fighter,
        "division": division,
        "tale_of_the_tape": fighter_stats,   # str_acc/td_def/reach/… or None
        "total_fights": int(len(fights)),
        "win_rate": round(float(fights["win(1)/loss(0)"].mean()) * 100, 1),
        "activity": activity,
        "timeline": timeline,
        "aged_well": aged,
        "avg_raw_perf": _scale_to_100(float(fights["Raw Perf"].mean()), "raw_perf"),
        "avg_adj_perf": _scale_to_100(avg_adj, "adj_perf"),
        "perf_label": _perf_label(_scale_to_100(avg_adj, "adj_perf")),
        "recent_perf": recent_perf,                  # last-3 form, same 0-100 scale
        "recent_record": recent_record,              # e.g. "2 - 1"
        "avg_opp_strength": _scale_to_100(avg_opp, "opp_str"),
        "opp_label": _opp_label(_scale_to_100(avg_opp, "opp_str")),
        "recent_opp_strength": _scale_to_100(recent_opp, "opp_str_recent"),
        "recent_opp_label": _opp_label(_scale_to_100(recent_opp, "opp_str_recent")),
        "volatility": volatility,
        "volatility_label": _volatility_label(vol),
        "career_score": round(float(score), 1),
        "career_label": label,
        "trajectory": trajectory,
        # The bucket behind the sentence, so the UI can pick an icon without
        # pattern-matching the prose. Matching display strings is how the
        # volatility check broke once already (see the comment above).
        "trajectory_bucket": bucket,
        "phases": {
            "early": _phase(early),
            "mid": _phase(mid),
            "late": _phase(late),
        },
        "record": record
    }
    return _json_safe(payload)

#memoization for performance    
_ranked_cache: dict[int, list] = {}


def _ranked_careers(min_fights):
    """Every fighter with >= min_fights, scored and sorted best-first."""
    cached = _ranked_cache.get(min_fights)
    if cached is not None:
        return cached

    df = _load()
    #GLOBAL MAX
    max_adj = df["Adj Perf"].max()
    #group by the fighters
    results = []
    for fighter, group in df.groupby("Fighter"):
        if len(group) < min_fights:
            continue
        score = _compute_career_score(group, max_adj)   # reuse the existing formula
        if pd.isna(score): #if unscorable skip
            continue

        results.append({
            "fighter": fighter,
            "career_score": round(float(score), 1),
            "total_fights": int(len(group)),
        })

    # sort highest first
    results.sort(key=lambda r: r["career_score"], reverse=True)
    _ranked_cache[min_fights] = results
    return results


def top_careers(n = 10, min_fights = 8):
    # slice a copy — callers must not be able to mutate the cached list
    return list(_ranked_careers(min_fights)[:n])
    

def _division(fights):
    """Where they campaign, by majority of their last 4 bouts rather than the
    most recent one — a single catchweight or a move up should not reassign
    a fighter. Lower-cased and stripped of title/interim noise. Shared by the
    profile and the tag so the two can never name different divisions."""
    recent_divisions = [
        re.sub(r"\b(ufc|interim|title|bout|championship)\b", " ", str(d).lower()).strip()
        for d in fights["division"].dropna().tail(4)
    ]
    recent_divisions = [re.sub(r"\s+", " ", d) for d in recent_divisions if d]
    return max(set(recent_divisions), key=recent_divisions.count) if recent_divisions else None


@lru_cache(maxsize=None)
def _fighter_tag_cached(name_norm):
    """The real work, memoized on the NORMALIZED name so "Jon Jones", "jon
    jones" and "Jon  Jones" all share one entry.

    Safe to cache forever with no TTL: everything here derives from the CSVs
    loaded in _load(), and those only change when refresh_data.py runs, which
    restarts the process — clearing this cache and _career_df together. The
    memo cannot outlive the data it was computed from.
    """
    df = _load()
    fights = df[df["Fighter_norm"] == name_norm].sort_values("fight_number")
    if fights.empty:
        return None

    # Only the numbers a tag or a fighter card needs. career_summary_api computes
    # the full timeline, the aged-well index and per-phase breakdowns as well,
    # which is ~6x the work for data a dot on an event page never shows.
    recent = fights.tail(RECENT_FORM_FIGHTS)
    recent_wins = int((recent["win(1)/loss(0)"] == 1).sum())
    opp_window = fights.tail(RECENT_OPP_FIGHTS)
    opp_wins = int((opp_window["win(1)/loss(0)"] == 1).sum())
    wins = int((fights["win(1)/loss(0)"] == 1).sum())

    return {
        # Overall figures for the fighter cards, scaled exactly as the profile's
        # rings (avg_adj_perf / avg_opp_strength) so a card and the profile
        # always show the same number.
        "overall_perf": _scale_to_100(float(fights["Adj Perf"].mean()), "adj_perf"),
        "overall_opp": _scale_to_100(float(fights["Opp Str"].mean()), "opp_str"),
        "record": f"{wins} - {len(fights) - wins}",
        "division": _division(fights),
        "career_score": round(float(_compute_career_score(fights, df["Adj Perf"].max())), 1),
        # Both already min-max scaled to 0-100 by _scale_to_100, using bounds
        # picked for the realistic career-average band — not the raw column
        # ranges. So these are directly comparable to each other and to score.
        "recent_form": _scale_to_100(_recent_form(fights), "adj_perf"),
        "strength_iq": _scale_to_100(float(opp_window["Opp Str"].mean()), "opp_str_recent"),
        "total_fights": int(len(fights)),
        "recent_record": f"{recent_wins} - {len(recent) - recent_wins}",
        "opp_record": f"{opp_wins} - {len(opp_window) - opp_wins}",   # W-L over the strength_iq window
    }


def fighter_tag(fighter):
    """Compact form/quality numbers for one fighter, or None if they aren't in
    the career data at all — debutants and short-notice replacements won't be,
    and the caller must render that as "no data" rather than as zeros, which
    would read as the worst fighter on the card."""
    tag = _fighter_tag_cached(normalize_name(fighter))
    # Copy: the cached dict is shared by every caller, so handing out the
    # original would let one of them mutate every future response.
    return dict(tag) if tag else None
