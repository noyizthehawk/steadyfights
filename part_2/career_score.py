"""
Compute a career score for each fighter
single source of truth
"""
import numpy as np

W_WIN = 0.45     # weight on raw win-rate within "career quality"
W_PERF = 0.55    # weight on opponent-adjusted performance

SOFT_CAP_KNEE = 90.0
SOFT_CAP_CEILING = 99.0   # FIFA's top rating; the curve approaches it, never reaches


def soft_cap(x):
    """Every rating's top end: a straight line up to the knee, then an
    exponential ease toward 99 that never reaches it. A hard min(x, 100)
    pinned Jones, Makhachev and Medic all at FORM 100, and GSP and Jones at
    career 100; past the knee the curve keeps separating them the way a FIFA
    card keeps 99 for the rare few. The ceiling is 99, not 100, because the
    page rounds: an asymptote at 100 still displayed "100" for values like
    99.6. The slope is 1 at the knee, so the scale doesn't kink there, and
    anything below 90 is untouched."""
    if x <= SOFT_CAP_KNEE:
        return x
    room = SOFT_CAP_CEILING - SOFT_CAP_KNEE
    return SOFT_CAP_KNEE + room * (1 - np.exp(-(x - SOFT_CAP_KNEE) / room))



def is_real_title(division):
    #what we exclude, this is for double champ checking
    d = str(division).lower()
    excluded = ["interim", "ultimate fighter", "tournament", "road to",
                "tuf nations", "ultimate ultimate", "ultimate japan"]
    return not any(x in d for x in excluded)


def compute_career_score(fights, max_adj_perf, *, win_col, perf_col,
                         title_col="title_fight", div_col="division",
                         opp_col="Opp Str"):

    # Credit for wins, debit for losses — and the two use OPPOSITE weights.
    #
    # The old form was sum(win*opp)/sum(opp), which put opponent quality in the
    # denominator for losses too. That made losing to a journeyman score BETTER
    # than losing to a champion: three wins over 0.60 opposition plus one loss
    # gave 0.800 against a 0.45 opponent but only 0.706 against a 0.75 one. It
    # treated a loss as a forfeited opportunity — bigger opponent, bigger loss —
    # when a loss should be evidence about the fighter.
    #
    # Now beating someone strong earns more (opp) and losing to someone weak
    # costs more (1 - opp), so the same three wins give 0.878 / 0.766 instead.
    opp_quality = fights[opp_col].clip(lower=0, upper=1)
    wins = fights[win_col]
    win_credit = (wins * opp_quality).sum()
    loss_debit = ((1 - wins) * (1 - opp_quality)).sum()
    total = win_credit + loss_debit
    quality_win_rate = win_credit / total if total > 0 else 0.0
    avg_adj_perf = fights[perf_col].mean()

    title_fights = fights[fights[title_col] == 1]
    num_title_fights = len(title_fights)
    num_title_wins = title_fights[win_col].sum()

    # Diminishing returns rather than a hard cap. The old
   
    #
    # Exponential decay never saturates, so the 16th win is still worth more
    # than the 15th, just far less than the 2nd.
    title_bonus = (
        0.05 * (1 - np.exp(-num_title_fights / 4.0))
        + 0.22 * (1 - np.exp(-num_title_wins / 2.0))
    )

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
    return soft_cap(score)
