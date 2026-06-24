"""
Compute a career score for each fighter
single source of truth
"""
import numpy as np

W_WIN = 0.45     # weight on raw win-rate within "career quality"
W_PERF = 0.55    # weight on opponent-adjusted performance



def is_real_title(division):
    #what we exclude, this is for double champ checking
    d = str(division).lower()
    excluded = ["interim", "ultimate fighter", "tournament", "road to",
                "tuf nations", "ultimate ultimate", "ultimate japan"]
    return not any(x in d for x in excluded)


def compute_career_score(fights, max_adj_perf, *, win_col, perf_col,
                         title_col="title_fight", div_col="division",
                         opp_col="Opp Str"):

    opp_quality = fights[opp_col].clip(lower=0)
    quality_win_rate = (
        (fights[win_col] * opp_quality).sum() / opp_quality.sum()
        if opp_quality.sum() > 0 else 0.0
    )
    avg_adj_perf = fights[perf_col].mean()

    title_fights = fights[fights[title_col] == 1]
    num_title_fights = len(title_fights)
    num_title_wins = title_fights[win_col].sum()
    title_bonus = min(0.01 * num_title_fights + 0.10 * num_title_wins, 0.25)

    real_title_wins = title_fights[
        (title_fights[win_col].astype(int) == 1)
        & (title_fights[div_col].apply(is_real_title).astype(bool))
    ]
    divisions_won = real_title_wins[div_col].str.lower().unique()
    double_champ_bonus = 0.03 if len(divisions_won) >= 2 else 0.0

    norm_adj_perf = avg_adj_perf / max_adj_perf
    career_quality_score = W_WIN * quality_win_rate + W_PERF * norm_adj_perf

    longevity_factor = min(np.sqrt(len(fights) / 25.0), 1.0)

    score = (
        0.7 * (career_quality_score + title_bonus + double_champ_bonus)
        + 0.3 * longevity_factor
    ) * 100
    return min(score, 100.0)
