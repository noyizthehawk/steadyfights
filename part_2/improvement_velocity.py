import pandas as pd
import numpy as np
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
fighter_csv = os.path.join(script_dir, "../csv/fighter_level_data.csv")

fighters_df = pd.read_csv(fighter_csv)

fighters_df['date'] = pd.to_datetime(fighters_df['date'])
print("Latest fight date in dataset:", fighters_df['date'].max())
fighters_df = fighters_df.sort_values(['id', 'date']).reset_index(drop=True)

# Compute fight time
fighters_df["fight_time_sec"] = (fighters_df["finish_round"] - 1) * 300 + fighters_df["match_time_sec"]
fighters_df["fight_time_min"] = fighters_df["fight_time_sec"] / 60

# Weights
weight_for_strikers = [0.35, 0.35, 0.05, 0.05, 0.20]
weight_for_grapplers = [0.05, 0.05, 0.35, 0.35, 0.20]
weight_for_balanced = [0.20, 0.20, 0.20, 0.20, 0.20]

# Per-minute metrics
fighters_df["sig_str_landed_per_min"] = fighters_df["sig_str_landed"] / fighters_df["fight_time_min"]
fighters_df["sig_str_absorbed_per_min"] = fighters_df["sig_str_absorbed"] / fighters_df["fight_time_min"]
fighters_df["td_landed_per_min"] = fighters_df["td_landed"] / fighters_df["fight_time_min"]
fighters_df["control_fraction"] = fighters_df["ctrl"] / fighters_df["fight_time_sec"]
fighters_df["strike_diff_per_min"] = fighters_df["sig_str_landed_per_min"] - fighters_df["sig_str_absorbed_per_min"]
fighters_df["td_acc_fight"] = (fighters_df["td_landed"] / fighters_df["td_atmpted"]).fillna(0)

# Z-scores for all metrics
fighters_df["strike_diff_z"] = (
    (fighters_df["strike_diff_per_min"] - fighters_df["strike_diff_per_min"].mean())
    / fighters_df["strike_diff_per_min"].std()
)
fighters_df["strike_acc_z"] = (
    (fighters_df["sig_str_acc"] - fighters_df["sig_str_acc"].mean())
    / fighters_df["sig_str_acc"].std()
)
fighters_df["td_acc_fight_z"] = (
    (fighters_df["td_acc_fight"] - fighters_df["td_acc_fight"].mean())
    / fighters_df["td_acc_fight"].std()
)
fighters_df["control_fraction_z"] = (
    (fighters_df["control_fraction"] - fighters_df["control_fraction"].mean())
    / fighters_df["control_fraction"].std()
)

# Style classification
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

# Style-weighted performance score
def compute_style_performance_score(row):
    win_flag = row.get('win_flag_indicator', 0)
    if row['style'] == 'Striker':
        weights = weight_for_strikers
    elif row['style'] == 'Grappler':
        weights = weight_for_grapplers
    else:
        weights = weight_for_balanced

    score = (
        row['strike_diff_z'] * weights[0] +
        row['strike_acc_z'] * weights[1] +
        row['td_acc_fight_z'] * weights[2] +
        row['control_fraction_z'] * weights[3] +
        win_flag * weights[4]
    )
    return score

fighters_df['style_performance_score'] = fighters_df.apply(compute_style_performance_score, axis=1)

# Min-max scaling to 0-100
min_score = fighters_df['style_performance_score'].min()
max_score = fighters_df['style_performance_score'].max()
fighters_df['performance_0_100'] = 100 * (fighters_df['style_performance_score'] - min_score) / (max_score - min_score)

# Weight-class specific normalization
fighters_df['wc_mean_perf'] = fighters_df.groupby('division')['performance_0_100'].transform('mean')
fighters_df['wc_std_perf'] = fighters_df.groupby('division')['performance_0_100'].transform('std')
fighters_df['wc_performance_z'] = (
    (fighters_df['performance_0_100'] - fighters_df['wc_mean_perf']) / fighters_df['wc_std_perf']
)

def performance_label(z):
    if z >= 1.5:
        return "Exceptional dominance"
    elif z >= 1.0:
        return "Elite dominance"
    elif z >= 0.5:
        return "Good dominance"
    elif z >= -0.5:
        return "Competitive performance"
    elif z >= -1.0:
        return "Below Average dominance"
    else:
        return "Outclassed"

fighters_df['performance_category'] = fighters_df['wc_performance_z'].apply(performance_label)
# Opponent strength calculation
print("Calculating opponent strength (optimized)...")

# Pre-compute running stats for each fighter
fighters_df['fight_count_before'] = fighters_df.groupby('id').cumcount()
fighters_df['running_win_rate'] = fighters_df.groupby('id')['win_flag_indicator'].transform(
    lambda x: x.expanding().mean().shift(1).fillna(0.5)
)
fighters_df['running_perf'] = fighters_df.groupby('id')['performance_0_100'].transform(
    lambda x: x.expanding().mean().shift(1).fillna(50)
)

# Create lookup dictionary for faster access
fighter_stats_lookup = {}
for idx, row in fighters_df.iterrows():
    key = (row['id'], row['date'])
    fighter_stats_lookup[key] = {
        'fight_count': row['fight_count_before'],
        'win_rate': row['running_win_rate'],
        'performance': row['running_perf']
    }

def calculate_opponent_strength_optimized(row):
    opponent_id = row['opponent_id']
    fight_date = row['date']

    # Look up opponent's stats at this date
    key = (opponent_id, fight_date)

    if key not in fighter_stats_lookup:
        return 0.5

    opp_stats = fighter_stats_lookup[key]
    fight_count = opp_stats['fight_count']

    if fight_count <= 2:
        return 0.5

    opp_win_rate = opp_stats['win_rate']
    opp_perf = opp_stats['performance'] / 100

    raw_strength = 0.5 * opp_win_rate + 0.5 * opp_perf
    confidence = min(fight_count / 8.0, 1.0)
    adjusted_strength = confidence * raw_strength + (1 - confidence) * 0.5

    return min(adjusted_strength, 0.75)

fighters_df['opponent_strength'] = fighters_df.apply(calculate_opponent_strength_optimized, axis=1)

print("Opponent strength calculated with no error")

def calculate_adjusted_performance(row):
    base_perf = row['performance_0_100']
    opp_str = row['opponent_strength']
    won = row['win_flag_indicator']
    fight_time = row['fight_time_sec']
    method_of_victory = row['method']

    if won == 1:
        # Wins: Boost based on opponent strength
        adjusted = base_perf * (0.5 + opp_str)
    elif method_of_victory == 'DQ':
        adjusted = base_perf
    else:
        # Losses: Apply penalty for short fight
        # normalize fight time
        duration_factor = min(fight_time / 900.0, 1.0)
        adjusted = base_perf * (0.4 + opp_str) * duration_factor

    return adjusted

fighters_df['adjusted_performance'] = fighters_df.apply(calculate_adjusted_performance, axis=1)

# Adjusted performance categorization
adj_mean = fighters_df['adjusted_performance'].mean()
adj_std = fighters_df['adjusted_performance'].std()

def adjusted_performance_label(value):
    if value >= adj_mean + 1.5 * adj_std:
        return "Dominant performance"
    elif value >= adj_mean + 1.0 * adj_std:
        return "Clear elite performance"
    elif value >= adj_mean + 0.5 * adj_std:
        return "Effective performance"
    elif value >= adj_mean - 0.5 * adj_std:
        return "High-level competitive fight"
    elif value >= adj_mean - 1.0 * adj_std:
        return "Ineffective performance"
    else:
        return "Outmatched performance"

fighters_df['adjusted_performance_category'] = fighters_df['adjusted_performance'].apply(
    adjusted_performance_label
)

fight_level_df = fighters_df[[
    'name',
    'fight_number',
    'opponent_name',
    'win_flag_indicator',
    'performance_0_100',
    'opponent_strength',
    'adjusted_performance',
    'adjusted_performance_category',
    'event_name'
]].copy()

# Rename for clarity
fight_level_df.rename(columns={
    'name': 'Fighter',
    'win_flag_indicator': 'win(1)/loss(0)',
    'performance_0_100': 'Raw Perf',
    'opponent_strength': 'Opp Str',
    'adjusted_performance': 'Adj Perf',
    'adjusted_performance_category': 'Category',
    'event_name': 'Event'
}, inplace=True)

# Save CSV
csv_dir = os.path.join(script_dir, "../csv")
os.makedirs(csv_dir, exist_ok=True)

fight_level_df.to_csv(
    os.path.join(csv_dir, "fighter_opponent_strength_extra.csv"),
    index=False
)
print("Fight-level CSV for all fighters saved!")
print("All calculations complete\n")

def compute_career_score(fighter_fights: pd.DataFrame) -> float:
    win_rate = fighter_fights['win_flag_indicator'].mean()
    avg_adj_perf = fighter_fights['adjusted_performance'].mean()

    title_fights = fighter_fights[fighter_fights['title_fight'] == 1]
    num_title_fights = len(title_fights)
    num_title_wins = title_fights['win_flag_indicator'].sum()

    title_bonus = 0.03 * num_title_fights + 0.10 * num_title_wins
    title_bonus = min(title_bonus, 0.25)

    max_adj_perf = fighters_df['adjusted_performance'].max()
    norm_adj_perf = avg_adj_perf / max_adj_perf

    career_quality_score = 0.6 * win_rate + 0.4 * norm_adj_perf

    total_fights = len(fighter_fights)
    longevity_factor = min(np.sqrt(total_fights / 25.0), 1.0)

    career_quality_title_adjusted = (
        0.7 * (career_quality_score + title_bonus) +
        0.3 * longevity_factor
    ) * 100

    return min(career_quality_title_adjusted, 100.0)


def get_top_careers_by_metric(top_n: int = 20, min_fights: int = 5):
    max_adj_perf = fighters_df['adjusted_performance'].max()
    results = []

    for fighter_name, group in fighters_df.groupby('name'):
        if len(group) < min_fights:
            continue

        fighter_fights = group.sort_values('fight_number')

        win_rate = fighter_fights['win_flag_indicator'].mean()
        avg_adj_perf = fighter_fights['adjusted_performance'].mean()

        title_fights = fighter_fights[fighter_fights['title_fight'] == 1]
        title_bonus = min(
            0.03 * len(title_fights) + 0.10 * title_fights['win_flag_indicator'].sum(),
            0.25
        )

        norm_adj_perf = avg_adj_perf / max_adj_perf
        career_quality_score = 0.6 * win_rate + 0.4 * norm_adj_perf
        longevity_factor = min(np.sqrt(len(fighter_fights) / 25.0), 1.0)

        score = min(
            (0.7 * (career_quality_score + title_bonus) + 0.3 * longevity_factor) * 100,
            100.0
        )

        results.append({
            'name': fighter_name,
            'career_quality_title_adjusted': score
        })

    return (
        pd.DataFrame(results)
        .sort_values('career_quality_title_adjusted', ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
# Fighter stats lookup function
def get_fighter_stats(fighter):
    fighter_name = fighter.strip()
    fighter_fights = fighters_df[fighters_df["name"] == fighter_name].sort_values("fight_number")

    if len(fighter_fights) > 0:
        print(f"\n{'='*80}")
        print(f"{fighter_name.upper()} - FIGHT-BY-FIGHT BREAKDOWN")
        print(f"{'='*80}\n")

        fighter_summary = fighter_fights[[
            'fight_number',
            'opponent_name',
            'win_flag_indicator',
            'performance_0_100',
            'opponent_strength',
            'adjusted_performance',
            'adjusted_performance_category',
            'event_name',
            'win_flag_indicator'
        ]].copy()

        fighter_summary.columns = [
            'Fight #',
            'Opponent',
            'Won',
            'Raw Perf',
            'Opp Str',
            'Adj Perf',
            'Category',
            'Event',
            'win(1)/loss(0)'
        ]

        print(fighter_summary.to_string(index=False))

        early_fights = fighter_fights[fighter_fights['fight_number'] <= 5]
        mid_fights = fighter_fights[(fighter_fights['fight_number'] >= 6) & (fighter_fights['fight_number'] <= 10)]
        late_fights = fighter_fights[fighter_fights['fight_number'] >= 11]

        print(f"\n{'='*80}")
        print(f"CAREER TRAJECTORY ANALYSIS")
        print(f"{'='*80}")

        # Determine trajectory for mid-career
        improvement_adj = mid_fights['adjusted_performance'].mean() - early_fights['adjusted_performance'].mean() if len(mid_fights) > 0 else 0
        if improvement_adj > 5:
            trajectory = "Rapid ascension — dominance increased against tougher competition"
        elif improvement_adj > 0:
            trajectory = "Steady development — performance improved as competition strengthened"
        elif improvement_adj > -3:
            trajectory = "Stabilization phase — faced elite opposition consistently"
        else:
            trajectory = "Late-career transition — competitive performances against top-tier opponents"
        if len(mid_fights) > 0:
            print(f"Mid-Career Trajectory: {trajectory}")

        print(f"\nEarly Career (Fights 1-5):")
        print(f"  Raw Performance: {early_fights['performance_0_100'].mean():.2f}")
        print(f"  Adjusted Performance: {early_fights['adjusted_performance'].mean():.2f}")
        print(f"  Avg Opponent Strength: {early_fights['opponent_strength'].mean():.3f}")
        print(f"  Win Rate: {early_fights['win_flag_indicator'].mean():.1%}")

        if len(mid_fights) > 0:
            print(f"\nMid Career (Fights 6-10):")
            print(f"  Raw Performance: {mid_fights['performance_0_100'].mean():.2f}")
            print(f"  Adjusted Performance: {mid_fights['adjusted_performance'].mean():.2f}")
            print(f"  Avg Opponent Strength: {mid_fights['opponent_strength'].mean():.3f}")
            print(f"  Win Rate: {mid_fights['win_flag_indicator'].mean():.1%}")

        if len(late_fights) > 0:
            print(f"\nLate Career (Fights 11+):")
            print(f"  Raw Performance: {late_fights['performance_0_100'].mean():.2f}")
            print(f"  Adjusted Performance: {late_fights['adjusted_performance'].mean():.2f}")
            print(f"  Avg Opponent Strength: {late_fights['opponent_strength'].mean():.3f}")
            print(f"  Win Rate: {late_fights['win_flag_indicator'].mean():.1%}")

        print(f"\n{'='*80}")
        print(f"OVERALL CAREER SUMMARY")
        print(f"{'='*80}")
        print(f"Total UFC Fights: {len(fighter_fights)}")
        print(f"Career Win Rate: {fighter_fights['win_flag_indicator'].mean():.1%}")
        print(f"Career Avg Performance (Raw): {fighter_fights['performance_0_100'].mean():.2f}")
        print(f"Career Avg Performance (Adjusted): {fighter_fights['adjusted_performance'].mean():.2f}")
        print(f"Performance Volatility: {fighter_fights['performance_0_100'].std():.2f}")

        # --- Title Fight Bonus


        title_fights = fighter_fights[fighter_fights['title_fight'] == 1]

        num_title_fights = len(title_fights)
        num_title_wins = title_fights['win_flag_indicator'].sum()
        title_bonus = (
            0.03 * num_title_fights +   # appearance bonus
            0.10 * num_title_wins        # win bonus
        )

        # Cap the bonus so belts don't dominate the score
        title_bonus = min(title_bonus, 0.25)

        win_rate = fighter_fights['win_flag_indicator'].mean()
        avg_adj_perf = fighter_fights['adjusted_performance'].mean()

        # Normalize adjusted performance to 0–1
        max_adj_perf = fighters_df['adjusted_performance'].max()
        norm_adj_perf = avg_adj_perf / max_adj_perf

        # --- Career Quality Score

        # Base career quality (performance + results)
        career_quality_score = (
            0.6 * win_rate +
            0.4 * norm_adj_perf
        )

        # --- Longevity
        total_fights = len(fighter_fights)

        #longevity scaling (diminishing returns)
        longevity_factor = min(np.sqrt(total_fights / 25.0), 1.0)

        # Adjusted Career Quality: 70% from career + title, 30% from longevity
        career_quality_title_adjusted = (
            0.7 * (career_quality_score + title_bonus) +
            0.3 * longevity_factor
        ) * 100

        # Cap Career Quality at 100
        career_quality_title_adjusted = min(career_quality_title_adjusted, 100.0)

        print(f"Career efficiency (Title-Adjusted): {career_quality_title_adjusted:.3f}")

        # Add narrative interpretation
        if career_quality_title_adjusted >= 90:
            career_label = "All-time dominant UFC career"
        elif career_quality_title_adjusted >= 80:
            career_label = "Elite championship career"
        elif career_quality_title_adjusted >= 70:
            career_label = "Sustained elite competitor at the top level"
        elif career_quality_title_adjusted >= 60:
            career_label = "High-level UFC contender career"
        else:
            career_label = "Inconsistent or developing UFC career"
        print(f"Career Interpretation: {career_label}")
        print("Note: Career Quality reflects dominance and consistency relative to competition,\nnot head-to-head superiority or technical skill.(This isnt a goat ranking).\nWhat have you done with the cards you have been dealt")

    else:
        print(f"Fighter '{fighter_name}' not found")
        print("\nTry one of these fighters:")
        sample_fighters = fighters_df['name'].value_counts().head(20).index.tolist()
        for i, name in enumerate(sample_fighters, 1):
            print(f"  {i}. {name}")
def print_model_memo() -> None:
    memo = """
=============================
MODEL MEMO (Quick Guide)
=============================

This tool outputs 3 key numbers per fight:

1) Raw Performance (0–100)
- “How well you performed” based on fight stats.
- Higher = more effective/efficient in your style (striking vs grappling weighting).
- It’s relative to this dataset (80 is “better than most fights here”, not “80% perfect”).

2) Opponent Strength (continuous, ~0.50 to 0.75)
- Continuous score, not a label.
- 0.50 = average/unknown opponent (or not enough prior data).
- It uses the opponent’s track record BEFORE the fight date and becomes more trusted as they have more fights.
- It’s capped at 0.75 so opponent boosts don’t dominate the model.

3) Adjusted Performance
- Context score: Raw Performance scaled by opponent strength and result.

How wins are treated:
- Beating stronger opponents increases Adjusted Performance more.

How losses are treated (yes, you get punished for getting finished early):
- Losses get a lower base multiplier than wins.
- Losses are also multiplied by a duration factor:
  * short loss (quick finish) -> bigger penalty
  * long loss (competitive late) -> smaller penalty

Reading tips:
- High Raw + low Opp Str -> looked great vs weaker/unknown competition.
- Medium Raw + high Opp Str -> solid work vs strong competition.
- Low Adjusted in a loss -> often a short/early loss.

Note:
This is NOT a “GOAT” or head-to-head ranking. It’s measuring consistency + dominance vs competition.
=============================
"""

    print(memo)
if __name__ == "__main__":

    print("Welcome to the UFC Fighter Analysis Tool to get best careers in UFC History!")
    print("Options:")
    print("1. Enter fighter name to analyze:")
    print("2. List top N fighters by Career Quality:")
    print("3. Memo(information about the model and how to read it)")
    print("4. Exit")
    option = input("\nEnter your option: ")
    #with error handling
    if option not in ["1", "2", "3", "4"]:
        print("Invalid option. Please try again.")

    while option != "4":
        if option == "1":
            fighter_name_input = input("\nEnter fighter name for analysis: ")
            get_fighter_stats(fighter_name_input)
        elif option == "2":
            top_n = int(input("Enter the number of top fighters to display: "))
            top_careers = get_top_careers_by_metric(top_n)
            print(f"\nTop {top_n} fighters by Career Quality:")
            b = 0
            for i, row in top_careers.iterrows():
                b += 1
                print(f"{b}. {row['name']} - Career Quality: {row['career_quality_title_adjusted']:.2f}")
        elif option == "3":
            print_model_memo()
        option = input("\nEnter your option: ")