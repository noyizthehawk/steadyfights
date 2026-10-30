"""Elo for every UFC fight — one implementation, shared.

Bout Brain trains on it (elo_before_fight is a model feature) and the career
profile uses it to judge how strong an opponent was on fight night. Moved out
of Prediction_model.train() so the two can never compute Elo differently.
"""
K_FACTOR = 32
INITIAL_ELO = 1500
ELO_INACTIVITY_DECAY = 0.85


def expected_score(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(elo_a, elo_b, actual_score_a, k=K_FACTOR):
    """Update Elo ratings after a fight."""
    expected_a = expected_score(elo_a, elo_b)
    new_elo_a = elo_a + k * (actual_score_a - expected_a)
    new_elo_b = elo_b + k * ((1 - actual_score_a) - (1 - expected_a))
    return new_elo_a, new_elo_b


def add_elo(fighters_df):
    """Fill `elo_before_fight` and `opponent_elo_before_fight` IN PLACE and
    return every fighter's final rating.

    `fighters_df` is fighter-level (one row per fighter per fight, with
    fight_id, name and winner) and must already be sorted by date: ratings are
    replayed in row order. Fights without exactly two rows are skipped; a
    draw or no contest scores 0.5.

    Each fight's two rows are looked up from a prebuilt position map rather
    than by filtering the whole table per fight: same replay order, same
    result, but ~13s became well under a second, which matters now that the
    web app runs this too."""
    elo_ratings = {}

    names = fighters_df['name'].to_numpy()
    winners = fighters_df['winner'].to_numpy()
    fight_ids = fighters_df['fight_id'].to_numpy()
    elo_before = [0.0] * len(fighters_df)
    opp_before = [0.0] * len(fighters_df)

    rows_of = {}                      # fight_id -> its row positions, in table order
    for pos, fight_id in enumerate(fight_ids):
        rows_of.setdefault(fight_id, []).append(pos)

    processed_fights = set()
    for fight_id in fight_ids:        # replay in table (date) order
        if fight_id in processed_fights:
            continue
        rows = rows_of[fight_id]
        if len(rows) != 2:
            continue
        a, b = rows

        name_a, name_b = names[a], names[b]
        elo_a = elo_ratings.get(name_a, INITIAL_ELO)
        elo_b = elo_ratings.get(name_b, INITIAL_ELO)

        elo_before[a], elo_before[b] = elo_a, elo_b
        opp_before[a], opp_before[b] = elo_b, elo_a

        winner = winners[a]
        if winner == name_a:
            actual_score_a = 1.0
        elif winner == name_b:
            actual_score_a = 0.0
        else:
            actual_score_a = 0.5

        new_elo_a, new_elo_b = update_elo(elo_a, elo_b, actual_score_a)
        elo_ratings[name_a] = new_elo_a
        elo_ratings[name_b] = new_elo_b
        processed_fights.add(fight_id)

    fighters_df['elo_before_fight'] = elo_before
    fighters_df['opponent_elo_before_fight'] = opp_before
    return elo_ratings
