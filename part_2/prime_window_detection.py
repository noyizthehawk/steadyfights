import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
# Load prepared data
# Get the folder where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Build paths relative to script folder
csv_input_path = os.path.join(script_dir, "../csv/fighter_level_data.csv")
output_dir = os.path.join(script_dir, "analysis_images_part_2")

# Make sure output folder exists
os.makedirs(output_dir, exist_ok=True)
# ====================== LOAD DATA ======================
fighter_df = pd.read_csv(csv_input_path)

print(f"\n{'='*60}")
print(f"PRIME WINDOW DETECTION ANALYSIS")
print(f"{'='*60}")
print(f"Loaded {len(fighter_df)} fighter-fight records")
print(f"Unique fighters: {fighter_df['name'].nunique()}")

#minimum 5 fights in the UFC
min_fights = 5
fighter_counts = fighter_df['name'].value_counts()
qualified_fighters = fighter_counts[fighter_counts >= min_fights].index
fighter_df_filtered = fighter_df[fighter_df['name'].isin(qualified_fighters)].copy()

print(f"Fighters with {min_fights}+ fights: {len(qualified_fighters)}")
print(f"Total fights analyzed: {len(fighter_df_filtered)}")

def assign_career_stage(fight_number):
    if fight_number <= 5:
        return 'Early (1-5)'
    elif fight_number <= 10:
        return 'Mid (6-10)'
    elif fight_number <= 15:
        return 'Prime (11-15)'
    else:
        return 'Late (16+)'

fighter_df_filtered['career_stage'] = fighter_df_filtered['fight_number'].apply(assign_career_stage)

# Calculate average win rate by career stage
stage_performance = fighter_df_filtered.groupby('career_stage').agg({
    'win_flag_indicator': 'mean',
    'age_at_fight': 'mean',  
    'fight_number': 'count'
}).round(3)

stage_performance.columns = ['Win Rate', 'Average Age', 'Number of Fights']  # ← UPDATE THIS

print(f"\n{'='*60}")
print(f"WIN RATE BY CAREER STAGE")
print(f"{'='*60}")
print(stage_performance)

#  Find Individual Fighter Peak Windows


def find_peak_window(fighter_data):
    """Find the fight number where fighter had highest rolling win rate"""
    if len(fighter_data) < 5:
        return None
    
    # Use rolling_win_rate_5 (more stable than 3)
    peak_idx = fighter_data['rolling_win_rate_5'].idxmax()
    
    if pd.isna(peak_idx):
        return None
    
    return fighter_data.loc[peak_idx, 'fight_number']

peak_windows = []

for fighter_name in qualified_fighters:
    fighter_data = fighter_df_filtered[fighter_df_filtered['name'] == fighter_name]
    peak_fight = find_peak_window(fighter_data)
    
    if peak_fight is not None:
        peak_windows.append({
            'fighter': fighter_name,
            'peak_fight_number': peak_fight,
            'total_fights': len(fighter_data)
        })

peak_df = pd.DataFrame(peak_windows)

print(f"\n{'='*60}")
print(f"WHEN DO FIGHTERS PEAK?")
print(f"{'='*60}")
print(f"Average peak occurs at fight: {peak_df['peak_fight_number'].mean():.1f}")
print(f"Median peak occurs at fight: {peak_df['peak_fight_number'].median():.1f}")
print(f"Most common peak fight: {peak_df['peak_fight_number'].mode().values[0]}")

#visulaize

plt.figure(figsize=(14, 6))

# Histogram of when fighters peak
plt.subplot(1, 2, 1)
plt.hist(peak_df['peak_fight_number'], bins=20, edgecolor='black', alpha=0.7, color='steelblue')
plt.xlabel('Fight Number at Peak Performance', fontsize=11)
plt.ylabel('Number of Fighters', fontsize=11)
plt.title('Distribution of Peak Performance Timing', fontsize=13, fontweight='bold')
plt.axvline(peak_df['peak_fight_number'].mean(), color='red', linestyle='--', 
            linewidth=2, label=f'Mean: {peak_df["peak_fight_number"].mean():.1f}')
plt.axvline(peak_df['peak_fight_number'].median(), color='orange', linestyle='--', 
            linewidth=2, label=f'Median: {peak_df["peak_fight_number"].median():.1f}')
plt.legend()
plt.grid(True, alpha=0.3)

# Win rate by career stage
plt.subplot(1, 2, 2)
stage_order = ['Early (1-5)', 'Mid (6-10)', 'Prime (11-15)', 'Late (16+)']
stage_data = stage_performance.loc[stage_order, 'Win Rate']
bars = plt.bar(range(len(stage_data)), stage_data, edgecolor='black', alpha=0.7, color='coral')
plt.xlabel('Career Stage', fontsize=11)
plt.ylabel('Win Rate', fontsize=11)
plt.title('Win Rate by Career Stage', fontsize=13, fontweight='bold')
plt.xticks(range(len(stage_data)), stage_order, rotation=45, ha='right')
plt.ylim(0, 1)
plt.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for i, bar in enumerate(bars):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.3f}', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
output_path = os.path.join(output_dir, "prime_window_analysis.png")
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n Saved visualization: {output_path}")

plt.show()

print(f"\n{'='*60}")
print(f"ANALYSIS COMPLETE")
print(f"{'='*60}\n")
