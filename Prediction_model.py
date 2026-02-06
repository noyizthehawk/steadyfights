import pandas as pd
import numpy as np
import os
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# --- Load CSVs ---
script_dir = os.path.dirname(os.path.abspath(__file__))
fighter_csv = os.path.join(script_dir, "csv/fighter_level_data.csv")
opp_strength_csv = os.path.join(script_dir, "csv/fighter_opponent_strength_extra.csv")

fighters_df = pd.read_csv(fighter_csv)
opp_strength_df = pd.read_csv(opp_strength_csv)

# Merge opponent strength
fighters_df = fighters_df.merge(
    opp_strength_df[['Fighter', 'fight_number', 'Opp Str']],
    left_on=['name', 'fight_number'],
    right_on=['Fighter', 'fight_number'],
    how='left'
)
fighters_df.drop(columns=['Fighter'], inplace=True)
fighters_df.rename(columns={'Opp Str': 'opponent_strength'}, inplace=True)

# rolling opponent strengths --- additional feature for predicting fight outcomes
fighters_df['rolling_opponent_strength_3'] = (
    fighters_df.groupby('name')['opponent_strength']
    .shift(1)
    .rolling(3, min_periods=1)
    .mean()
)
fighters_df['rolling_opponent_strength_5'] = (
    fighters_df.groupby('name')['opponent_strength']
    .shift(1)
    .rolling(5, min_periods=1)
    .mean()
)
fighters_df['rolling_opponent_strength_3'] = fighters_df['rolling_opponent_strength_3'].fillna(fighters_df['opponent_strength'].mean())
fighters_df['rolling_opponent_strength_5'] = fighters_df['rolling_opponent_strength_5'].fillna(fighters_df['opponent_strength'].mean())

# Compute fighter style per fight
def group_fight_style(row):
    TD_ATTEMPTS_PM = 0.4
    STR_LANDED_PM = 3.5
    td_attempts_pm = row['td_atmpted'] / row['fight_time_min']
    sig_landed_pm = row['sig_str_landed'] / row['fight_time_min']

    if td_attempts_pm >= TD_ATTEMPTS_PM and sig_landed_pm < STR_LANDED_PM:
        return 'Grappler'
    if sig_landed_pm >= STR_LANDED_PM and td_attempts_pm < TD_ATTEMPTS_PM:
        return 'Striker'
    return 'Balanced'

fighters_df['style'] = fighters_df.apply(group_fight_style, axis=1)

# Encode style as numeric (one-hot)
style_dummies = pd.get_dummies(fighters_df['style'], prefix='style')
fighters_df = pd.concat([fighters_df, style_dummies], axis=1)

# --- Keep relevant features ---
features_to_keep = [
    "fight_id", "id", "name", "winner",
    "rolling_win_rate_5", "rolling_win_rate_3",
    "rolling_slpm_5", "rolling_slpm_3",
    "rolling_sapm_5", "rolling_sapm_3",
    "rolling_td_acc_5", "rolling_td_acc_3",
    "rolling_td_def_5", "rolling_td_def_3",
    "age_at_fight", "reach", "days_since_last_fight",
    "rolling_opponent_strength_3", "rolling_opponent_strength_5"
] + list(style_dummies.columns)

fighters_new_df = fighters_df[features_to_keep].copy()

#  Merge fighters into fight pairs
merged = fighters_new_df.merge(
    fighters_new_df, on='fight_id', suffixes=('_A', '_B')
)
merged = merged[merged['name_A'] != merged['name_B']]
merged = merged[merged['id_A'] < merged['id_B']]

# diferences for numeric features
numeric_features = [
    "rolling_win_rate_5","rolling_win_rate_3",
    "rolling_slpm_5","rolling_slpm_3",
    "rolling_sapm_5","rolling_sapm_3",
    "rolling_td_acc_5","rolling_td_acc_3",
    "rolling_td_def_5","rolling_td_def_3",
    "age_at_fight","reach","days_since_last_fight",
    "rolling_opponent_strength_3","rolling_opponent_strength_5"
]
# --- Compute differences for numeric features ---
for f in numeric_features:
    merged[f"diff_{f}"] = merged[f"{f}_A"] - merged[f"{f}_B"]

# --- Differences for style (one-hot) ---
style_features = list(style_dummies.columns)
for f in style_features:
    # Convert boolean to int first
    merged[f"diff_{f}"] = merged[f"{f}_A"].astype(int) - merged[f"{f}_B"].astype(int)

# Additional engineered features to help xgboost, this is non linesr
merged['diff_win_rate_x_opp_strength'] = merged['diff_rolling_win_rate_5'] * merged['diff_rolling_opponent_strength_5']
merged['diff_striking_efficiency'] = merged['diff_rolling_slpm_3'] - merged['diff_rolling_sapm_3']
merged['diff_grappling_score'] = merged['diff_rolling_td_acc_3'] + merged['diff_rolling_td_def_3']
merged['diff_experience_factor'] = merged['diff_age_at_fight'] - merged['diff_days_since_last_fight'] / 365
merged['diff_momentum'] = merged['diff_rolling_win_rate_3'] - merged['diff_rolling_win_rate_5']

# Interaction of style with opponent strength / win rate
for s in style_features:
    merged[f"diff_{s}_x_winrate"] = merged[f"diff_{s}"] * merged['diff_rolling_win_rate_5']
    merged[f"diff_{s}_x_opp_strength"] = merged[f"diff_{s}"] * merged['diff_rolling_opponent_strength_5']

# --- Final feature list ---
diff_features = [col for col in merged.columns if col.startswith('diff_')]

# --- Target ---
merged["target"] = (merged["winner_A"] == merged["name_A"]).astype(int)

X = merged[diff_features].fillna(0)
y = merged["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# --- XGBoost model ---
model = xgb.XGBClassifier(
    #may tinker with these parameter to reduce overfitting
    max_depth=3,
    learning_rate=0.01,
    n_estimators=300,
    subsample=0.7,
    colsample_bytree=0.7,

    min_child_weight=5,
    gamma=0.3,

    reg_alpha=0.5,
    reg_lambda=1.5,

    objective='binary:logistic',
    eval_metric='logloss'
)
model.fit(X_train, y_train)

train_preds = model.predict(X_train)
test_preds = model.predict(X_test)

train_acc = accuracy_score(y_train, train_preds)
test_acc = accuracy_score(y_test, test_preds)

print("\nTrain Accuracy:", train_acc)
print("Test Accuracy:", test_acc)
print("\nClassification Report:")
print(classification_report(y_test, test_preds))

# Feature importance
importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nTop Features:")
print(importance.head(20))

# --- Interactive UFC fight simulator ---
def prepare_fighter_features(fighter_row, style_columns):
    # Compute style one-hot again for the prediction (latest stats)
    fighter_row['style'] = group_fight_style(fighter_row)
    for s in style_columns:
        fighter_row[f'style_{s}'] = 1 if fighter_row['style'] == s else 0
    return fighter_row

def compute_diff_features(fighter_A, fighter_B, numeric_features, style_columns):
    diff = {}

    for f in numeric_features:
        diff[f"diff_{f}"] = fighter_A[f] - fighter_B[f]

    for s in style_columns:
        diff[f"diff_{s}"] = fighter_A[f"style_{s}"] - fighter_B[f"style_{s}"]
        diff[f"diff_{s}_x_winrate"] = diff[f"diff_{s}"] * (fighter_A['rolling_win_rate_5'] - fighter_B['rolling_win_rate_5'])
        diff[f"diff_{s}_x_opp_strength"] = diff[f"diff_{s}"] * (fighter_A['rolling_opponent_strength_5'] - fighter_B['rolling_opponent_strength_5'])

    diff['diff_win_rate_x_opp_strength'] = (fighter_A['rolling_win_rate_5'] - fighter_B['rolling_win_rate_5']) * (fighter_A['rolling_opponent_strength_5'] - fighter_B['rolling_opponent_strength_5'])
    diff['diff_striking_efficiency'] = (fighter_A['rolling_slpm_3'] - fighter_B['rolling_slpm_3']) - (fighter_A['rolling_sapm_3'] - fighter_B['rolling_sapm_3'])
    diff['diff_grappling_score'] = (fighter_A['rolling_td_acc_3'] - fighter_B['rolling_td_acc_3']) + (fighter_A['rolling_td_def_3'] - fighter_B['rolling_td_def_3'])
    diff['diff_experience_factor'] = (fighter_A['age_at_fight'] - fighter_B['age_at_fight']) - ((fighter_A['days_since_last_fight'] - fighter_B['days_since_last_fight'])/365)
    diff['diff_momentum'] = (fighter_A['rolling_win_rate_3'] - fighter_B['rolling_win_rate_3']) - (fighter_A['rolling_win_rate_5'] - fighter_B['rolling_win_rate_5'])

    return pd.DataFrame([diff])

def predict_fight(fighter_A_name, fighter_B_name):
    try:
        fighter_A = fighters_df[fighters_df['name'] == fighter_A_name].iloc[-1]
        fighter_B = fighters_df[fighters_df['name'] == fighter_B_name].iloc[-1]
    except IndexError:
        print("One or both fighter names not found. Check spelling!")
        return

    fighter_A = prepare_fighter_features(fighter_A.copy(), style_features)
    fighter_B = prepare_fighter_features(fighter_B.copy(), style_features)

    X = compute_diff_features(fighter_A, fighter_B, numeric_features, style_features)
    X = X[diff_features]
    prob = model.predict_proba(X)[0]


    print(f"\nPrediction: {fighter_A_name} vs {fighter_B_name}")
    print(f"{fighter_A_name} win probability: {prob[1]:.2f}")
    print(f"{fighter_B_name} win probability: {prob[0]:.2f}\n")


print("\n=== UFC Fight Simulator ===")
print("Type 'exit' to quit")
while True:
    fight_input = input("Enter fight (FighterA vs FighterB): ").strip()
    if fight_input.lower() == 'exit':
        break
    if 'vs' not in fight_input.lower():
        print("Use format: FighterA vs FighterB")
        continue
    try:
        fighter1, fighter2 = [f.strip() for f in fight_input.split('vs', 1)]
    except ValueError:
        print("Invalid input! Make sure to type 'FighterA vs FighterB'.")
        continue
    predict_fight(fighter1, fighter2)