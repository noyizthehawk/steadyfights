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
    # min(0.01*fights + 0.10*wins, 0.25) maxed out at two title wins, so 60 of
    # the 388 fighters who ever fought for a belt scored identically — Jon Jones
    # with 16 title wins landed on the same 0.25 as a one-time champion.
    #
    # Exponential decay never saturates, so the 16th win is still worth more
    # than the 15th, just far less than the 2nd. The decay constant is 2: slower
    # decay punished short perfect title runs, dropping Khabib (4-0 in title
    # fights, retired undefeated) below fighters with twice the losses.
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
    return min(score, 100.0)
