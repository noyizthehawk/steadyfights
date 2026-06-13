import pandas as pd
import numpy as np
import os
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
script_dir = os.path.dirname(os.path.abspath(__file__))
fighter_csv = os.path.join(script_dir, "../csv/fighter_level_data.csv")
opp_strength_csv = os.path.join(script_dir, "../csv/fighter_opponent_strength_extra.csv")

#  elo rating system constants
K_FACTOR = 32
INITIAL_ELO = 1500
VERBOSE = False

FEATURE_LABELS = {
    "diff_elo_before_fight": "Elo rating",
    "diff_reach": "Reach",
    "diff_rolling_finish_rate_5": "Finish rate (last 5)",
    "diff_age_at_fight": "Age",
    "diff_height": "Height",
    }


def expected_score(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(elo_a, elo_b, actual_score_a, k=K_FACTOR):
    expected_a = expected_score(elo_a, elo_b)
    new_elo_a = elo_a + k * (actual_score_a - expected_a)
    new_elo_b = elo_b + k * ((1 - actual_score_a) - (1 - expected_a))
    return new_elo_a, new_elo_b


def predict_fight(fighter_a, fighter_b):
    fa = fighters_df[fighters_df["name"] == fighter_a].sort_values("date").iloc[-1]
    fb = fighters_df[fighters_df["name"] == fighter_b].sort_values("date").iloc[-1]

    row = {}

    for feature in numeric_features_to_diff:
        row[f"diff_{feature}"] = fa[feature] - fb[feature]

    row["diff_stance_Orthodox"] = int(fa.get("stance_Orthodox", 0)) - int(fb.get("stance_Orthodox", 0))
    row["diff_stance_Southpaw"] = int(fa.get("stance_Southpaw", 0)) - int(fb.get("stance_Southpaw", 0))
    row["diff_stance_Switch"] = int(fa.get("stance_Switch", 0)) - int(fb.get("stance_Switch", 0))

    X_pred = pd.DataFrame([row])[diff_features].fillna(0)
    probs = calibrated_ensemble.predict_proba(X_pred)[0]

    print("\n==============================")
    print(f"{fighter_a} ({fa['style_name']}) vs {fighter_b} ({fb['style_name']})")
    print("==============================")
    print(f"{fighter_a} Win Probability: {probs[1] * 100:.2f}%")
    print(f"{fighter_b} Win Probability: {probs[0] * 100:.2f}%")

    winner = fighter_a if probs[1] > probs[0] else fighter_b
    confidence = max(probs) * 100
    print(f"\nModel Pick: {winner} ({confidence:.1f}% confidence)")
    print("==============================\n")


def predict_fight_api(fighter_a, fighter_b):
    """Same logic as predict_fight, but returns a JSON-serializable dict
    instead of printing. This is what the web backend calls."""
    fa = fighters_df[fighters_df["name"] == fighter_a].sort_values("date").iloc[-1]
    fb = fighters_df[fighters_df["name"] == fighter_b].sort_values("date").iloc[-1]

    row = {}
    for feature in numeric_features_to_diff:
        row[f"diff_{feature}"] = fa[feature] - fb[feature]
    row["diff_stance_Orthodox"] = int(fa.get("stance_Orthodox", 0)) - int(fb.get("stance_Orthodox", 0))
    row["diff_stance_Southpaw"] = int(fa.get("stance_Southpaw", 0)) - int(fb.get("stance_Southpaw", 0))
    row["diff_stance_Switch"] = int(fa.get("stance_Switch", 0)) - int(fb.get("stance_Switch", 0))

    X_pred = pd.DataFrame([row])[diff_features].fillna(0)
    probs = calibrated_ensemble.predict_proba(X_pred)[0]

    factors = []
    for feat, label in FEATURE_LABELS.items():
        diff = row.get(feat, 0)
        std  = feature_stds.get(feat, 0)
        if not std:                      # skip if std is 0 this is bad data
            continue
        impact = abs(diff / std)         # how many std-devs apart -> for ranking
        favors = fighter_a if diff > 0 else fighter_b   # diff is A - B, so + = A
        factors.append({
            "label":  label,
            "favors": favors,
            "detail": abs(round(float(diff), 1)),    # the raw gap, for display
            "_impact": impact,           # temporary, only used to sort
        })

    factors.sort(key=lambda f: f["_impact"], reverse=True)   # biggest first
    top_factors = factors[:3]
    for f in top_factors:
        del f["_impact"]

    prob_a = float(probs[1])
    prob_b = float(probs[0])
    winner = fighter_a if prob_a > prob_b else fighter_b
    return {
        "fighter_a": fighter_a,
        "fighter_b": fighter_b,
        "style_a": str(fa.get("style_name", "")),
        "style_b": str(fb.get("style_name", "")),
        "prob_a": round(prob_a * 100, 2),
        "prob_b": round(prob_b * 100, 2),
        "pick": winner,
        "confidence": round(max(prob_a, prob_b) * 100, 1),
        "factors": top_factors,
    }


def list_fighters():
    """Sorted unique fighter names the model knows about (for dropdowns)."""
    return sorted(fighters_df["name"].dropna().unique().tolist())


def train():
    global feature_stds
    global fighters_df, calibrated_ensemble, diff_features, numeric_features_to_diff

    
    fighters_df = pd.read_csv(fighter_csv)
    opp_strength_df = pd.read_csv(opp_strength_csv)

    

    # Merge opponent strength
    fighters_df = fighters_df.merge(
        opp_strength_df[['Fighter', 'fight_number', 'Adj Perf', 'Opp Str']],
        left_on=['name', 'fight_number'],
        right_on=['Fighter', 'fight_number'],
        how='left'
    )
    fighters_df.drop(columns=['Fighter'], inplace=True)
    fighters_df.rename(columns={'Opp Str': 'opponent_strength'}, inplace=True)
    fighters_df.rename(columns={'Adj Perf': 'adjusted_performance'}, inplace=True)

    #  elo rating system
    fighters_df['date'] = pd.to_datetime(fighters_df['date'])
    fighters_df['dob'] = pd.to_datetime(fighters_df['dob'])
    fighters_df = fighters_df.sort_values('date').reset_index(drop=True)

    # Initialize Elo tracking
    elo_ratings = {}

    fighters_df['elo_before_fight'] = 0.0
    fighters_df['opponent_elo_before_fight'] = 0.0

    processed_fights = set()
    for idx, row in fighters_df.iterrows():
        fight_id = row['fight_id']
        fighter_name = row['name']
        if fight_id in processed_fights:
            continue
        fight_rows = fighters_df[fighters_df['fight_id'] == fight_id]

        if len(fight_rows) != 2:
            continue

        fighter_a = fight_rows.iloc[0]
        fighter_b = fight_rows.iloc[1]

        name_a = fighter_a['name']
        name_b = fighter_b['name']
        elo_a = elo_ratings.get(name_a, INITIAL_ELO)
        elo_b = elo_ratings.get(name_b, INITIAL_ELO)

        fighters_df.loc[fight_rows.index[0], 'elo_before_fight'] = elo_a
        fighters_df.loc[fight_rows.index[1], 'elo_before_fight'] = elo_b
        fighters_df.loc[fight_rows.index[0], 'opponent_elo_before_fight'] = elo_b
        fighters_df.loc[fight_rows.index[1], 'opponent_elo_before_fight'] = elo_a

        winner = fighter_a['winner']
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

    fighters_df['elo_diff'] = fighters_df['elo_before_fight'] - fighters_df['opponent_elo_before_fight']

    # Physical features
    fighters_df['age_at_fight'] = ((fighters_df['date'] - fighters_df['dob']).dt.days / 365.25).round(2)
    stance_dummies = pd.get_dummies(fighters_df['stance'], prefix='stance')
    fighters_df = pd.concat([fighters_df, stance_dummies], axis=1)
    fighters_df.drop(columns=['stance'], inplace=True)

    # Striking derivation
    fighters_df["striking_differential_3"] = fighters_df["rolling_slpm_3"] - fighters_df["rolling_sapm_3"]
    fighters_df["striking_differential_5"] = fighters_df["rolling_slpm_5"] - fighters_df["rolling_sapm_5"]

    fighters_df["str_acc_fight"] = (
            fighters_df["sig_str_landed"] / fighters_df["sig_str_atmpted"]
    ).fillna(0)

    fighters_df["rolling_str_acc_3"] = (
        fighters_df.groupby("name")["str_acc_fight"]
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_str_acc_5"] = (
        fighters_df.groupby("name")["str_acc_fight"]
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_str_acc_3"] = fighters_df["rolling_str_acc_3"].fillna(0)
    fighters_df["rolling_str_acc_5"] = fighters_df["rolling_str_acc_5"].fillna(0)

    # Rolling opponent features
    fighters_df['rolling_opp_elo_3'] = (
        fighters_df.groupby('name')['opponent_elo_before_fight']
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df['rolling_opp_elo_5'] = (
        fighters_df.groupby('name')['opponent_elo_before_fight']
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df['rolling_opp_elo_3'] = fighters_df['rolling_opp_elo_3'].fillna(INITIAL_ELO)
    fighters_df['rolling_opp_elo_5'] = fighters_df['rolling_opp_elo_5'].fillna(INITIAL_ELO)

    fighters_df['rolling_opponent_strength_3'] = (
        fighters_df.groupby('name')['opponent_strength']
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df['rolling_opponent_strength_5'] = (
        fighters_df.groupby('name')['opponent_strength']
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    # Rolling TD volume
    fighters_df['rolling_td_avg_5'] = (
        fighters_df.groupby('name')['td_avg']
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df['rolling_td_avg_5'] = fighters_df['rolling_td_avg_5'].fillna(0)

    # Rolling submission attempts
    fighters_df['rolling_sub_avg_5'] = (
        fighters_df.groupby('name')['sub_avg']
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df['rolling_sub_avg_5'] = fighters_df['rolling_sub_avg_5'].fillna(0)

    # Rolling striking defense
    fighters_df['rolling_str_def_5'] = (
        fighters_df.groupby('name')['str_def']
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df['rolling_str_def_5'] = fighters_df['rolling_str_def_5'].fillna(0)
    fighters_df['rolling_opponent_strength_3'] = fighters_df['rolling_opponent_strength_3'].fillna(0)
    fighters_df['rolling_opponent_strength_5'] = fighters_df['rolling_opponent_strength_5'].fillna(0)

    #clustering of fight styles
    print("\nCalculating fighter styles...")
    print("===============================")
    if VERBOSE:

        print([col for col in fighters_df.columns if 'td' in col.lower() or 'sub' in col.lower() or 'str_def' in col.lower()])

    fighter_style_stats = fighters_df.groupby('name').tail(5).groupby('name').agg({
        'rolling_slpm_5': 'mean',
        'rolling_sapm_5': 'mean',
        'rolling_td_acc_5': 'mean',
        'rolling_td_def_5': 'mean',
        'rolling_td_avg_5': 'mean',       # takedown volume — key for Chimaev types
        'rolling_sub_avg_5': 'mean',      # submission attempts
        'rolling_str_def_5': 'mean',      # striking defense
        'striking_differential_5': 'mean',
    }).reset_index()

    fighter_style_stats = fighter_style_stats.dropna()

    style_features = [
        'rolling_slpm_5',
        'rolling_sapm_5',
        'rolling_td_acc_5',
        'rolling_td_def_5',
        'rolling_td_avg_5',
        'rolling_sub_avg_5',
        'rolling_str_def_5',
        'striking_differential_5'
    ]

    scaler = StandardScaler()
    X_style = scaler.fit_transform(fighter_style_stats[style_features])

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    fighter_style_stats['style_cluster'] = kmeans.fit_predict(X_style)

    cluster_profiles = fighter_style_stats.groupby('style_cluster')[style_features].mean()

    # Rank clusters by key metrics to assign labels intelligently
    td_vol_rank = cluster_profiles['rolling_td_avg_5'].rank(ascending=False)
    td_acc_rank = cluster_profiles['rolling_td_acc_5'].rank(ascending=False)
    slpm_rank = cluster_profiles['rolling_slpm_5'].rank(ascending=False)
    sub_rank = cluster_profiles['rolling_sub_avg_5'].rank(ascending=False)
    str_def_rank = cluster_profiles['rolling_str_def_5'].rank(ascending=False)
    diff_rank = cluster_profiles['striking_differential_5'].rank(ascending=False)

    # Score each cluster for different archetypes
    grappler_score = td_vol_rank + td_acc_rank + sub_rank          # high TD volume + accuracy + subs
    complete_score = td_vol_rank + slpm_rank + diff_rank           # high everywhere (Chimaev, Usman)
    striker_score = slpm_rank + diff_rank                          # high striking output + differential
    counter_score = str_def_rank + diff_rank                       # good defense, controlled striking
    wrestler_score = td_vol_rank + td_acc_rank                     # TD volume focused, less striking

    assigned = set()
    style_names = {}

    archetypes = [
        ("Complete Fighter", complete_score),
        ("Grappler", grappler_score),
        ("Striker", striker_score),
        ("Counter Striker", counter_score),
        ("Wrestler", wrestler_score),
    ]

    for label, score in archetypes:
        # Pick best unassigned cluster for this archetype
        ranked = score.sort_values().index.tolist()
        for cluster_id in ranked:
            if cluster_id not in assigned:
                style_names[cluster_id] = label
                assigned.add(cluster_id)
                break

    fighter_style_stats['style_name'] = fighter_style_stats['style_cluster'].map(style_names)

    if VERBOSE:
        print("\nCluster Profiles:")
        for cid, name in style_names.items():
            profile = cluster_profiles.loc[cid]
            print(
                f"  {name}: SLPM={profile['rolling_slpm_5']:.2f}, "
                f"TD_avg={profile['rolling_td_avg_5']:.2f}, "
                f"TD_acc={profile['rolling_td_acc_5']:.2f}, "
                f"Subs={profile['rolling_sub_avg_5']:.2f}, "
                f"StrDiff={profile['striking_differential_5']:.2f}"
            )
    fighters_df = fighters_df.merge(
        fighter_style_stats[['name', 'style_cluster', 'style_name']],
        on='name',
        how='left'
    )

    most_common_style = fighters_df['style_cluster'].mode()[0]
    fighters_df['style_cluster'] = fighters_df['style_cluster'].fillna(most_common_style)
    fighters_df['style_name'] = fighters_df['style_name'].fillna(style_names[most_common_style])

    # ================== END STYLE CLUSTERING ==================

    # --- Finish rate feature ---
    # Did THIS fighter win this fight by finish (KO/TKO or submission, not a decision)?
    # method examples: "KO/TKO", "Submission", "SUB Rear Naked Choke" -> finish;
    #                  "Decision - Unanimous", "U-DEC" -> not a finish.
    fighters_df["won_by_finish"] = (
        (fighters_df["winner"] == fighters_df["name"])
        & fighters_df["method"].str.contains("KO|SUB", case=False, na=False)
    ).astype(int)

    # Rolling finish rate over the fighter's PAST 5 fights. transform keeps the
    # rolling window INSIDE each fighter's own history; shift(1) excludes the
    # current fight so we never peek at the result we're trying to predict.
    fighters_df["rolling_finish_rate_5"] = (
        fighters_df.groupby("name")["won_by_finish"]
        .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
        .fillna(0)
    )

    # Numeric features to difference
    numeric_features_to_diff = [
        "elo_before_fight",
        "rolling_slpm_3", "rolling_slpm_5",
        "rolling_sapm_3", "rolling_sapm_5",
        "striking_differential_3", "striking_differential_5",
        "rolling_str_acc_3", "rolling_str_acc_5",
        "rolling_td_acc_3", "rolling_td_acc_5",
        "rolling_td_def_3", "rolling_td_def_5",
        "rolling_win_rate_3", "rolling_win_rate_5",
        "weight", "height", "reach", "age_at_fight",
        "days_since_last_fight", "fight_number",
        "rolling_opp_elo_3", "rolling_opp_elo_5",
        "rolling_opponent_strength_3", "rolling_opponent_strength_5",
        "opponent_strength",
        "style_cluster",
        "rolling_finish_rate_5"
    ]

    # Create fight pairs
    merged = fighters_df.merge(
        fighters_df, on='fight_id', suffixes=('_A', '_B')
    )
    merged = merged[merged['name_A'] != merged['name_B']]
    merged = merged[merged['id_A'] < merged['id_B']]

    # Differences for numeric features
    for feature in numeric_features_to_diff:
        merged[f"diff_{feature}"] = merged[f"{feature}_A"] - merged[f"{feature}_B"]

    merged['diff_stance_Orthodox'] = merged['stance_Orthodox_A'].astype(int) - merged['stance_Orthodox_B'].astype(int)
    merged['diff_stance_Southpaw'] = merged['stance_Southpaw_A'].astype(int) - merged['stance_Southpaw_B'].astype(int)
    merged['diff_stance_Switch'] = merged['stance_Switch_A'].astype(int) - merged['stance_Switch_B'].astype(int)

    # Target
    merged["target"] = (merged["winner_A"] == merged["name_A"]).astype(int)
    diff_features = [col for col in merged.columns if col.startswith('diff_')]

    # Model training — TEMPORAL split (train on the past, test on the most recent
    # fights). This mirrors reality: you only ever predict FUTURE fights. A random
    # split lets future fights leak into training and gives an optimistic number.
    merged = merged.sort_values('date_A').reset_index(drop=True)
    X = merged[diff_features].fillna(0)
    feature_stds = X.std()
    y = merged["target"]

    split_idx = int(len(merged) * 0.8)            # earliest 80% -> train
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # --- Symmetry augmentation (TRAINING SET ONLY) ---
    # Every feature is a difference (A - B), so swapping the two fighters simply
    # negates the whole feature row and flips the label. Adding these mirrored rows
    # doubles the training data and forces the model to be order-invariant, i.e.
    # predict(A, B) == 1 - predict(B, A).
    # We do this AFTER the split and only on the train set — mirroring before the
    # split would put each test fight's mirror into training (leakage = fake boost).
    X_train = pd.concat([X_train, -X_train], ignore_index=True)
    y_train = pd.concat([y_train, 1 - y_train], ignore_index=True)

    # Balanced config: enough capacity to use the signal, regularized enough to
    # keep the train/test gap sane (the loose config overfit to a 11-pt gap).
    xgb_model = xgb.XGBClassifier(
        max_depth=4,
        learning_rate=0.02,
        n_estimators=400,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=0.1,
        reg_alpha=0.3,
        reg_lambda=1.2,
        objective='binary:logistic',
        eval_metric='logloss',
        random_state=42
    )

    rf_model = RandomForestClassifier(
        n_estimators=400,
        max_depth=8,            # middle ground (was 6 tight / 12 overfit)
        min_samples_leaf=10,    # middle ground (was 20 tight / 5 overfit)
        random_state=42
    )

    lr_model = LogisticRegression(
        max_iter=5000,
        C=0.5                   # middle ground (was 0.3 tight / 1.0 loose)
    )

    ensemble = VotingClassifier(
        estimators=[
            ('xgb', xgb_model),
            ('rf', rf_model),
            ('lr', lr_model)
        ],
        voting='soft'
    )

    calibrated_ensemble = CalibratedClassifierCV(
        ensemble,
        method="sigmoid",
        cv=5
    )

    calibrated_ensemble.fit(X_train, y_train)
    test_probs = calibrated_ensemble.predict_proba(X_test)
    test_preds = (test_probs[:, 1] > 0.5).astype(int)

    print(f"\nTest Accuracy: {accuracy_score(y_test, test_preds) * 100:.2f}%")
    train_probs = calibrated_ensemble.predict_proba(X_train)
    train_preds = (train_probs[:, 1] > 0.5).astype(int)
    print(f"Training Accuracy: {accuracy_score(y_train, train_preds) * 100:.2f}%")


def main():
    """CLI entry point: train once, then loop on terminal input (unchanged)."""
    train()
    while True:
        print("FIGHT PREDICTOR")
        f1 = input("Enter Fighter A (or 'exit'): ")
        if f1.lower() == "exit":
            break
        f2 = input("Enter Fighter B: ")
        if f1 not in fighters_df["name"].values or f2 not in fighters_df["name"].values:
            print("One or both fighters not found.")
            continue

        predict_fight(f1, f2)


if __name__ == "__main__":
    main()