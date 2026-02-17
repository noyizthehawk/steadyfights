import pandas as pd
import numpy as np


def base_clean(path):
    df = pd.read_csv(
        path,
        na_values=["", " ", "NA", "N/A", "null", "None", "none"]
    )

    # column names
    df.columns = (
        df.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
    )

    # trim strings
    obj_cols = df.select_dtypes(include="object").columns
    df[obj_cols] = df[obj_cols].apply(lambda s: s.str.strip())

    # remove duplicates
    df = df.drop_duplicates()

    return df


def clean_ufc():
    df = base_clean("Uncleaned/UFC.csv")

    for c in ["r_dob", "b_dob"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    return df


def clean_event():
    df = base_clean("Uncleaned/event_details.csv")

    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors="coerce")

    return df

def clean_fight():
    df = base_clean("Uncleaned/fight_details.csv")

    # Convert all relevant numeric columns to float
    numeric_cols = [col for col in df.columns if any(x in col for x in [
        'kd','td','sig','sub','ground','ctrl','head','body','leg','dist','clinch','total','avg','per'
    ])] + ['finish_round','match_time_sec','total_rounds']

    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    return df


def clean_fighter():
    df = base_clean("Uncleaned/fighter_details.csv")

    # Numeric columns
    numeric_cols = [
        "wins", "losses", "draws",
        "height", "weight", "reach",
        "splm","str_acc","sapm","str_def",
        "td_avg","td_avg_acc","td_def",
        "sub_avg"
    ]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Date column
    if 'dob' in df.columns:
        df['dob'] = pd.to_datetime(df['dob'], errors='coerce')

    return df


if __name__ == "__main__":
    # clean each dataset and save
    clean_ufc().to_csv("csv/UFC_clean.csv", index=False)
    clean_event().to_csv("csv/event_clean.csv", index=False)
    clean_fight().to_csv("csv/fight_clean.csv", index=False)
    clean_fighter().to_csv("csv/fighter_clean.csv", index=False)

    print("All datasets cleaned and saved:")
    print("- UFC_clean.csv")
    print("- event_clean.csv")
    print("- fight_clean.csv")
    print("- fighter_clean.csv")