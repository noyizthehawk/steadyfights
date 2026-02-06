import pandas as pd
import numpy as np
import os
# PREPARING THE DATA FOR FIGHTER ANALYSIS

def red_corner_fighters(ufc_dataset):
    cols_not_b = [c for c in ufc_dataset.columns if not c.startswith("b_")] # Exclude blue corner columns
    r_filtered_df = ufc_dataset[cols_not_b].copy() # Keep only red corner columns
    r_filtered_df["sig_str_absorbed"] = ufc_dataset["b_sig_str_landed"]
    r_filtered_df["td_defense"] = np.where(
        ufc_dataset["b_td_atmpted"] > 0,
        1 - (ufc_dataset["b_td_landed"] / ufc_dataset["b_td_atmpted"]),
        1.0
    )
    r_filtered_df["opponent_id"] = ufc_dataset["b_id"]
    r_filtered_df["opponent_name"] = ufc_dataset["b_name"]
    r_filtered_df =r_filtered_df.rename(columns=lambda c: c[2:] if c.startswith("r_") else c) #renamecols
    return r_filtered_df

def blue_corner_fighters(ufc_dataset):
    cols_not_r = [c for c in ufc_dataset.columns if not c.startswith("r_")]
    b_filtered_df = ufc_dataset[cols_not_r].copy()
    b_filtered_df["sig_str_absorbed"] = ufc_dataset["r_sig_str_landed"]
    b_filtered_df["td_defense"] = np.where(
        ufc_dataset["r_td_atmpted"] > 0,
        1 - (ufc_dataset["r_td_landed"] / ufc_dataset["r_td_atmpted"]),
        1.0
    )
    b_filtered_df["opponent_id"] = ufc_dataset["r_id"]
    b_filtered_df["opponent_name"] = ufc_dataset["r_name"]
    b_filtered_df = b_filtered_df.rename(columns=lambda c: c[2:] if c.startswith("b_") else c)
    return b_filtered_df


def merge_red_blue(red_df, blue_df):
    merged_df = pd.concat([red_df, blue_df], ignore_index=True)
    return merged_df
    
    

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    csv_input_path = os.path.join(script_dir, "../csv/UFC_clean.csv")  # input CSV
    csv_output_path = os.path.join(script_dir, "../csv/fighter_level_data.csv")
    ufc_dataset = pd.read_csv(csv_input_path)

    red_corner =red_corner_fighters(ufc_dataset)
    blue_corner = blue_corner_fighters(ufc_dataset)

    # Merge red and blue corner fighters
    fighters_df = merge_red_blue(red_corner, blue_corner)
    
    fighters_df["date"] = pd.to_datetime(fighters_df["date"])
    fighters_df["dob"] = pd.to_datetime(fighters_df["dob"])  # date of birth

    fighters_df = fighters_df.sort_values(by=["name", "date"])
    fighters_df["fight_number"] = fighters_df.groupby("name").cumcount() + 1
    # days since last fight
    fighters_df["days_since_last_fight"] = fighters_df.groupby("name")["date"].diff().dt.days

    #age at fight
    fighters_df["age_at_fight"] = ((fighters_df["date"] - fighters_df["dob"]).dt.days / 365.25).round(2)
    #winner column
    fighters_df['win_flag_indicator'] = (fighters_df['winner'] == fighters_df['name']).astype(int)
    
    #rolling rates
    # Fight time in minutes
    fighters_df["fight_time_min"] = (fighters_df["finish_round"] - 1) * 300 + fighters_df["match_time_sec"]
    fighters_df["fight_time_min"] = fighters_df["fight_time_min"] / 60

    # Striking per minute
    fighters_df["sig_str_landed_per_min"] = fighters_df["sig_str_landed"] / fighters_df["fight_time_min"]
    fighters_df["sig_str_absorbed_per_min"] = fighters_df["sig_str_absorbed"] / fighters_df["fight_time_min"]

    # Takedown accuracy
    fighters_df["td_acc_fight"] = (fighters_df["td_landed"] / fighters_df["td_atmpted"]).fillna(0)

    # ========================== rolling rates ================================
    # --- STRIKING ---
    fighters_df["rolling_slpm_3"] = (
        fighters_df.groupby("name")["sig_str_landed_per_min"]
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_slpm_5"] = (
        fighters_df.groupby("name")["sig_str_landed_per_min"]
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )

    fighters_df["rolling_sapm_3"] = (
        fighters_df.groupby("name")["sig_str_absorbed_per_min"]
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_sapm_5"] = (
        fighters_df.groupby("name")["sig_str_absorbed_per_min"]
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )

    # Fill NaNs with dataset mean (first fights)
    fighters_df["rolling_slpm_3"] = fighters_df["rolling_slpm_3"].fillna(
        fighters_df["sig_str_landed_per_min"].mean()
    )
    fighters_df["rolling_slpm_5"] = fighters_df["rolling_slpm_5"].fillna(
        fighters_df["sig_str_landed_per_min"].mean()
    )
    fighters_df["rolling_sapm_3"] = fighters_df["rolling_sapm_3"].fillna(
        fighters_df["sig_str_absorbed_per_min"].mean()
    )
    fighters_df["rolling_sapm_5"] = fighters_df["rolling_sapm_5"].fillna(
        fighters_df["sig_str_absorbed_per_min"].mean()
    )

    # --- GRAPPLING ---
    fighters_df["rolling_td_acc_3"] = (
        fighters_df.groupby("name")["td_acc_fight"]
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_td_acc_5"] = (
        fighters_df.groupby("name")["td_acc_fight"]
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_td_def_3"] = (
        fighters_df.groupby("name")["td_defense"]
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_td_def_5"] = (
        fighters_df.groupby("name")["td_defense"]
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )

    # Fill NaNs with dataset mean
    fighters_df["rolling_td_acc_3"] = fighters_df["rolling_td_acc_3"].fillna(
        fighters_df["td_acc_fight"].mean()
    )
    fighters_df["rolling_td_acc_5"] = fighters_df["rolling_td_acc_5"].fillna(
        fighters_df["td_acc_fight"].mean()
    )
    fighters_df["rolling_td_def_3"] = fighters_df["rolling_td_def_3"].fillna(
        fighters_df["td_defense"].mean()
    )
    fighters_df["rolling_td_def_5"] = fighters_df["rolling_td_def_5"].fillna(
        fighters_df["td_defense"].mean()
    )

    # --- WIN RATE ---
    fighters_df["rolling_win_rate_3"] = (
        fighters_df.groupby("name")["win_flag_indicator"]
        .shift(1)
        .rolling(3, min_periods=1)
        .mean()
        .round(2)
    )
    fighters_df["rolling_win_rate_5"] = (
        fighters_df.groupby("name")["win_flag_indicator"]
        .shift(1)
        .rolling(5, min_periods=1)
        .mean()
        .round(2)
    )

    # Fill first-fight NaNs with neutral 0.5
    fighters_df["rolling_win_rate_3"] = fighters_df["rolling_win_rate_3"].fillna(0.5)
    fighters_df["rolling_win_rate_5"] = fighters_df["rolling_win_rate_5"].fillna(0.5)
    # Write merged DataFrame to CSV
    fighters_df.to_csv(csv_output_path, index=False)
