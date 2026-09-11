
"""
Career analysis for the web API.
"""
import os

import numpy as np
import pandas as pd
from unidecode import unidecode

from part_2.career_score import compute_career_score


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
        pd.read_csv(fighter_csv)[["name", "fight_number", "title_fight", "division", "date"]]
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


# Cut points per metric. adj and vol gain a split at the median because the old
# p25-p75 band held HALF the roster under a single label, which told a user
# nothing. opp does NOT get one: 39% of fights carry the 0.500 opponent-strength
# placeholder, so its p25 and p50 are both exactly 0.50 and any band between
# them would be unreachable — a label that could never render.
_QUANTILES = {
    "adj": (0.25, 0.50, 0.75, 0.90),
    "vol": (0.25, 0.50, 0.75, 0.90),
    "opp": (0.25, 0.75, 0.90),
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
    """Map value to a label. `labels` has len(edges)+1 entries, low band first."""
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
    "high":    ("Hot and cold — capable of anything on the night",
                "Was hot and cold — capable of anything on the night"),
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


def _perf_label(avg_adj):
    return _bucket(avg_adj, _get_thresholds()["adj"],
                   ["Developing", "Competitive Performances", "Solid Performances",
                    "Strong Performances", "Elite Performances"])


def _volatility_label(vol):
    # lower volatility = steadier, the lower the better
    return _bucket(vol, _get_thresholds()["vol"],
                   ["Very consistent performances", "Consistent Performances", "Fairly steady",
                    "Streaky", "Unpredictable performances"])


def _opp_label(avg_opp):
    return _bucket(avg_opp, _get_thresholds()["opp"],
                   ["Lighter competition", "Average competition", "Tough competition", "Elite competition"])


# Observed min/max of per-fighter career AVERAGES (fighters with >=3 fights),
# used to min-max normalize each stat onto 0-100 for display: the weakest career
# average maps to ~0, the strongest to ~100.
_SCALE_BOUNDS = {
    "raw_perf": (30.0, 70.0),
    "adj_perf": (3.0, 65.0),
    "opp_str":  (0.42, 0.63),
}


def _scale_to_100(value, kind):
    """Min-max normalize a career-average stat onto 0-100, clamped to the ends."""
    lo, hi = _SCALE_BOUNDS[kind]
    scaled = (value - lo) / (hi - lo) * 100
    return round(min(100.0, max(0.0, scaled)), 1)


def _compute_career_score(fights, max_adj_perf):
    """Thin adapter over the shared scorer, passing career.py's column names."""
    return compute_career_score(
        fights, max_adj_perf,
        win_col="win(1)/loss(0)", perf_col="Adj Perf",
    )


def _phase(sub):
    """Aggregate one career phase (early/mid/late), or None if it has no fights."""
    if sub.empty:
        return None
    # Per-fight log for this phase — drives the drill-down when a user clicks the tile.
    bouts = [
        {
            "fight_number": int(r["fight_number"]),
            "opponent": r["opponent_name"],
            "won": bool(int(r["win(1)/loss(0)"])),
            "event": r["Event"],
            "adj_perf": round(float(r["Adj Perf"]), 1),
        }
        for _, r in sub.sort_values("fight_number").iterrows()
    ]
    return {
        "fights": int(len(sub)),
        "win_rate": round(float(sub["win(1)/loss(0)"].mean()) * 100, 1),
        
        "raw_perf": round(float(sub["Raw Perf"].mean()), 1),
        "adj_perf": round(float(sub["Adj Perf"].mean()), 1),
    
        "opp_strength": round(float(sub["Opp Str"].mean()), 3),
        "bouts": bouts,
    }
_aged_well_index = None


def _aged_index():
    """Two lookups behind the 'aged well' view, built once and cached.

    opp_history — every strength reading each fighter ever recorded AS an
    opponent, date-sorted. The max of the readings AFTER a given fight is what
    they went on to become.

    title_wins — every date each fighter won a title fight, sorted. A peak alone
    can't tell you someone became champion; Opp Str blends win rate and
    performance and knows nothing about belts.
    """
    global _aged_well_index
    if _aged_well_index is not None:
        return _aged_well_index

    df = _load()
    history = {}
    for name, g in df[["opponent_name", "date", "Opp Str"]].dropna().groupby("opponent_name"):
        g = g.sort_values("date")
        history[name] = (g["date"].tolist(), g["Opp Str"].tolist())

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
            "perf": round(float(r["Raw Perf"]), 1),
            "adj_perf": round(float(r["Adj Perf"]), 1),
            "opp": round(float(r["Opp Str"]), 3),
        }
        for _, r in fights.iterrows()
        if pd.notna(r["Raw Perf"]) and pd.notna(r["Opp Str"])
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

        then = float(r["Opp Str"])
        gain = (peak_after - then) if peak_after is not None else 0.0
        # a flat reading is usually the <3-fight placeholder (39% of rows), not a
        # verdict, so it must not qualify as a story
        if (gain > 0.05 or became_champ) and opp_name not in seen_opponents:
            seen_opponents.add(opp_name)
            aged.append({
                "fight_number": int(r["fight_number"]),
                "opponent": opp_name,
                "won": bool(int(r["win(1)/loss(0)"])),
                "event": r["Event"],
                "then": round(then, 3),
                "peak_after": round(float(peak_after), 3) if peak_after is not None else None,
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

    # Recent form: the last (up to) 5 fights, scored on the SAME 0-100 scale as
    # avg_adj_perf so it's directly comparable to the career number. This captures
    # "how good are they RIGHT NOW" — a fighter who improved late (e.g. Oliveira)
    # scores high here even if their career average is dragged down by early years.
    recent = fights.tail(5)
    recent_perf = _scale_to_100(float(recent["Adj Perf"].mean()), "adj_perf")
    recent_wins = int((recent["win(1)/loss(0)"] == 1).sum())
    recent_record = f"{recent_wins} - {len(recent) - recent_wins}"

    fighter_stats = get_fighter_stats(fighter)

    return {
        "fighter": fighter,
        "tale_of_the_tape": fighter_stats,   # str_acc/td_def/reach/… or None
        "total_fights": int(len(fights)),
        "win_rate": round(float(fights["win(1)/loss(0)"].mean()) * 100, 1),
        "activity": activity,
        "timeline": timeline,
        "aged_well": aged,
        "avg_raw_perf": _scale_to_100(float(fights["Raw Perf"].mean()), "raw_perf"),
        "avg_adj_perf": _scale_to_100(avg_adj, "adj_perf"),
        "perf_label": _perf_label(avg_adj),          # label uses the RAW average
        "recent_perf": recent_perf,                  # last-5 form, same 0-100 scale
        "recent_record": recent_record,              # e.g. "4 - 1"
        "avg_opp_strength": _scale_to_100(avg_opp, "opp_str"),
        "opp_label": _opp_label(avg_opp),            # label uses the RAW average
        "volatility": volatility,
        "volatility_label": _volatility_label(vol),
        "career_score": round(float(score), 1),
        "career_label": label,
        "trajectory": trajectory,
        "phases": {
            "early": _phase(early),
            "mid": _phase(mid),
            "late": _phase(late),
        },
        "record": record
    }

def top_careers(n = 10, min_fights = 8):
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

    # sort highest first, then take the top n
    results.sort(key=lambda r: r["career_score"], reverse=True)
    return results[:n]
    