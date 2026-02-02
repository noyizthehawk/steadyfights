import pandas as pd
# HOW FIGHTERS CHANGE OVER TIME

def red_corner_fighters(ufc_dataset):
    cols_not_b = [c for c in ufc_dataset.columns if not c.startswith("b_")] # Exclude blue corner columns
    r_filtered_df = ufc_dataset[cols_not_b].copy() # Keep only red corner columns
    r_filtered_df["sig_str_absorbed"] = ufc_dataset["b_sig_str_landed"]
    r_filtered_df["opponent_id"] = ufc_dataset["b_id"]
    r_filtered_df["opponent_name"] = ufc_dataset["b_name"]
    r_filtered_df =r_filtered_df.rename(columns=lambda c: c[2:] if c.startswith("r_") else c) #renamecols
    return r_filtered_df

def blue_corner_fighters(ufc_dataset):
    cols_not_r = [c for c in ufc_dataset.columns if not c.startswith("r_")]
    b_filtered_df = ufc_dataset[cols_not_r].copy()
    b_filtered_df["sig_str_absorbed"] = ufc_dataset["r_sig_str_landed"]
    b_filtered_df["opponent_id"] = ufc_dataset["r_id"]
    b_filtered_df["opponent_name"] = ufc_dataset["r_name"]
    b_filtered_df = b_filtered_df.rename(columns=lambda c: c[2:] if c.startswith("b_") else c)
    return b_filtered_df


def merge_red_blue(red_df, blue_df):
    merged_df = pd.concat([red_df, blue_df], ignore_index=True)
    return merged_df
    
    

if __name__ == "__main__":
    ufc_dataset = pd.read_csv("csv/UFC_clean.csv")
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
    fighters_df["rolling_win_rate_3"] = (
        fighters_df.groupby("name")["win_flag_indicator"]
        .shift(1).rolling(3, min_periods=1).mean()
        .reset_index(0, drop=True).round(2)
    )
    fighters_df["rolling_win_rate_5"] = (
        fighters_df.groupby("name")["win_flag_indicator"]
        .shift(1).rolling(5, min_periods=1).mean()
        .reset_index(0, drop=True).round(2)
    )
    fighters_df["rolling_sig_str_landed_3"] = (
        fighters_df.groupby("name")["sig_str_landed"]
        .shift(1).rolling(3, min_periods=1).mean()
        .reset_index(0, drop=True).round(2)
    )
    fighters_df["rolling_sig_str_absorbed_3"] = (
        fighters_df.groupby("name")["sig_str_absorbed"]
        .shift(1).rolling(3, min_periods=1).mean()
        .reset_index(0, drop=True).round(2)
    )
    fighters_df["rolling_sig_str_landed_5"] = (
        fighters_df.groupby("name")["sig_str_landed"]
        .shift(1).rolling(5, min_periods=1).mean()
        .reset_index(0, drop=True).round(2)
    )
    fighters_df["rolling_sig_str_absorbed_5"] = (
        fighters_df.groupby("name")["sig_str_absorbed"]
        .shift(1).rolling(5, min_periods=1).mean()
        .reset_index(0, drop=True).round(2)
    )
   
    # Write merged DataFrame to CSV
    fighters_df.to_csv("csv/fighter_level_data.csv", index=False)
