"""
Career analysis for the web API.
"""
import os

import numpy as np
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
career_csv = os.path.join(script_dir, "../csv/fighter_opponent_strength_extra.csv")
fighter_csv = os.path.join(script_dir, "../csv/fighter_level_data.csv")

# Loaded once on first use and cached (the CSVs don't change while the server runs;
# a data refresh restarts the process, which re-reads them).
_career_df = None


def _load():
    """Load and cache the per-fight career table, with title_fight/division joined in."""
    global _career_df
    if _career_df is not None:
        return _career_df

    career = pd.read_csv(career_csv)
    # compute_career_score needs title_fight + division, which live in the
    # fighter-level data. Join on fighter name and fight number 
    extra = (
        pd.read_csv(fighter_csv)[["name", "fight_number", "title_fight", "division"]]
        .drop_duplicates(subset=["name", "fight_number"])
    )
    career = career.merge(
        extra,
        left_on=["Fighter", "fight_number"],
        right_on=["name", "fight_number"],
        how="left",
    )
    _career_df = career
    return career


def _is_real_title(division):
    """A real belt  excludes, TUF, tournaments()"""
    d = str(division).lower()
    excluded = ["ultimate fighter", "tournament", "road to",
                "tuf nations", "ultimate ultimate", "ultimate japan"]
    return not any(x in d for x in excluded)


def _compute_career_score(fights, max_adj_perf):
    """Career quality score (0-100). Ported from improvement_velocity.compute_career_score,
    adapted to this CSV's column names ('win(1)/loss(0)', 'Adj Perf')."""
    win_rate = fights["win(1)/loss(0)"].mean()
    avg_adj_perf = fights["Adj Perf"].mean()

    title_fights = fights[fights["title_fight"] == 1]
    num_title_fights = len(title_fights)
    num_title_wins = title_fights["win(1)/loss(0)"].sum()

    title_bonus = min(0.03 * num_title_fights + 0.10 * num_title_wins, 0.25)

    real_title_wins = title_fights[
        (title_fights["win(1)/loss(0)"].astype(int) == 1)
        & (title_fights["division"].apply(_is_real_title).astype(bool))
    ]
    divisions_won = real_title_wins["division"].str.lower().unique()
    double_champ_bonus = 0.03 if len(divisions_won) >= 2 else 0.0

    norm_adj_perf = avg_adj_perf / max_adj_perf
    career_quality_score = 0.6 * win_rate + 0.4 * norm_adj_perf

    longevity_factor = min(np.sqrt(len(fights) / 25.0), 1.0)

    score = (
        0.7 * (career_quality_score + title_bonus + double_champ_bonus)
        + 0.3 * longevity_factor
    ) * 100
    return min(score, 100.0)


def _phase(sub):
    """Aggregate one career phase (early/mid/late), or None if it has no fights."""
    if sub.empty:
        return None
    return {
        "fights": int(len(sub)),
        "win_rate": round(float(sub["win(1)/loss(0)"].mean()) * 100, 1),
        "raw_perf": round(float(sub["Raw Perf"].mean()), 1),
        "adj_perf": round(float(sub["Adj Perf"].mean()), 1),
        "opp_strength": round(float(sub["Opp Str"].mean()), 3),
    }


def career_summary_api(fighter):
    """Return n a JSON-serializable career rundown for one fighter or None if not found"""
    df = _load()
    fights = df[df["Fighter"] == fighter.strip()].sort_values("fight_number")
    if fights.empty:
        return None

    max_adj = df["Adj Perf"].max()

    # Career-phase buckets — used for the `phases` breakdown in the response.
    early = fights[fights["fight_number"] <= 5]
    mid = fights[(fights["fight_number"] >= 6) & (fights["fight_number"] <= 10)]
    late = fights[fights["fight_number"] >= 11]

    # Trajectory is recent form that is last 5 fights against everything before them.
    # Need at least 6 fights so there's a baseline to compare the last 5 against.
    if len(fights) <= 5:
        trajectory = "Developing career — not enough fights to assess trajectory"
    else:
        recent = fights.tail(5)          # most recent 5 fights (rows are sorted by fight_number)
        earlier = fights.iloc[:-5]       # everything before them
        improvement = recent["Adj Perf"].mean() - earlier["Adj Perf"].mean()

        if improvement > 5:
            trajectory = "On a tear right now, getting better the harder the fights get"
        elif improvement > 0:
            trajectory = "Leveling up,  holding their own as the competition gets stiffer"
        elif improvement > -3:
            trajectory = "Holding it down,  been grinding against top competition consistently"
        else:
            trajectory = "Deep in the trenches,  still showing up against the best in the game"

    score = _compute_career_score(fights, max_adj)
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

    return {
        "fighter": fighter,
        "total_fights": int(len(fights)),
        "win_rate": round(float(fights["win(1)/loss(0)"].mean()) * 100, 1),
        "avg_raw_perf": round(float(fights["Raw Perf"].mean()), 1),
        "avg_adj_perf": round(float(fights["Adj Perf"].mean()), 1),
        "volatility": volatility,
        "career_score": round(float(score), 1),
        "career_label": label,
        "trajectory": trajectory,
        "phases": {
            "early": _phase(early),
            "mid": _phase(mid),
            "late": _phase(late),
        },
    }
