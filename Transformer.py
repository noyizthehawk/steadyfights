import pandas as pd
import numpy as np
from datetime import datetime


# --- UTILITY FUNCTIONS ---
def parse_stat_value(stat_str):
    try:
        if 'of' in stat_str:
            parts = stat_str.split('of')
            return int(parts[0].strip()), int(parts[1].strip())
        return int(stat_str), 0
    except:
        return 0, 0


def parse_time_to_seconds(time_str):
    try:
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return 0


def parse_control_time(ctrl_str):
    return parse_time_to_seconds(ctrl_str)


def calculate_accuracy(landed, attempted):
    return round((landed / attempted) * 100, 2) if attempted else 0.0


def convert_height_to_cm(height_str):
    if not height_str or pd.isna(height_str): return None
    try:
        h = str(height_str).replace('"', '').replace("'", ' ').strip().split()
        if len(h) >= 2:
            total_inches = int(h[0]) * 12 + int(h[1])
            return round(total_inches * 2.54, 2)
    except:
        return None
    return None


def convert_weight_to_kg(weight_str):
    if not weight_str or pd.isna(weight_str): return None
    try:
        pounds = float(str(weight_str).replace('lbs.', '').replace('lbs', '').strip())
        return round(pounds / 2.20462, 2)
    except:
        return None
    return None


def convert_reach_to_cm(reach_str):
    if not reach_str or pd.isna(reach_str): return None
    try:
        inches = float(str(reach_str).replace('"', '').replace('in', '').strip())
        return round(inches * 2.54, 2)
    except:
        return None
    return None


def parse_date(date_str):
    if not date_str or pd.isna(date_str) or date_str == '--': return None
    try:
        return datetime.strptime(str(date_str).strip(), '%b %d, %Y').strftime('%Y-%m-%d')
    except:
        try:
            return datetime.strptime(str(date_str).strip(), '%d-%b-%y').strftime('%Y-%m-%d')
        except:
            return None
    return None


# --- TRANSFORM FUNCTION ---
def transform_to_ufc_clean_format(raw_df):
    transformed_rows = []
    for idx, row in raw_df.iterrows():
        try:
            fight_date = pd.to_datetime(row['Date'], errors='coerce').strftime('%Y-%m-%d')

            # RED corner
            r_kd = int(row['Kd_1']) if pd.notna(row['Kd_1']) else 0
            r_sig_landed, r_sig_atmpted = parse_stat_value(row['Sig. Str._1'])
            r_total_landed, r_total_atmpted = parse_stat_value(row['Total Str._1'])
            r_td_landed, r_td_atmpted = parse_stat_value(row['Td_1'])
            r_sub_att = int(row['Sub. Att_1']) if pd.notna(row['Sub. Att_1']) else 0
            r_ctrl = parse_control_time(row['Ctrl_1']) if pd.notna(row['Ctrl_1']) else 0
            r_head_landed, r_head_atmpted = parse_stat_value(row['Head_1'])
            r_body_landed, r_body_atmpted = parse_stat_value(row['Body_1'])
            r_leg_landed, r_leg_atmpted = parse_stat_value(row['Leg_1'])
            r_dist_landed, r_dist_atmpted = parse_stat_value(row['Distance_1'])
            r_clinch_landed, r_clinch_atmpted = parse_stat_value(row['Clinch_1'])
            r_ground_landed, r_ground_atmpted = parse_stat_value(row['Ground_1'])

            # RED accuracies
            r_sig_acc = calculate_accuracy(r_sig_landed, r_sig_atmpted)
            r_total_acc = calculate_accuracy(r_total_landed, r_total_atmpted)
            r_td_acc = calculate_accuracy(r_td_landed, r_td_atmpted)
            r_head_acc = calculate_accuracy(r_head_landed, r_head_atmpted)
            r_body_acc = calculate_accuracy(r_body_landed, r_body_atmpted)
            r_leg_acc = calculate_accuracy(r_leg_landed, r_leg_atmpted)
            r_dist_acc = calculate_accuracy(r_dist_landed, r_dist_atmpted)
            r_clinch_acc = calculate_accuracy(r_clinch_landed, r_clinch_atmpted)
            r_ground_acc = calculate_accuracy(r_ground_landed, r_ground_atmpted)
            total_sig_str = r_sig_landed
            r_lh_per = (r_head_landed / total_sig_str * 100) if total_sig_str else 0
            r_lb_per = (r_body_landed / total_sig_str * 100) if total_sig_str else 0
            r_ll_per = (r_leg_landed / total_sig_str * 100) if total_sig_str else 0
            r_ld_per = (r_dist_landed / total_sig_str * 100) if total_sig_str else 0
            r_lc_per = (r_clinch_landed / total_sig_str * 100) if total_sig_str else 0
            r_lg_per = (r_ground_landed / total_sig_str * 100) if total_sig_str else 0

            # BLUE corner
            b_kd = int(row['Kd_2']) if pd.notna(row['Kd_2']) else 0
            b_sig_landed, b_sig_atmpted = parse_stat_value(row['Sig. Str._2'])
            b_total_landed, b_total_atmpted = parse_stat_value(row['Total Str._2'])
            b_td_landed, b_td_atmpted = parse_stat_value(row['Td_2'])
            b_sub_att = int(row['Sub. Att_2']) if pd.notna(row['Sub. Att_2']) else 0
            b_ctrl = parse_control_time(row['Ctrl_2']) if pd.notna(row['Ctrl_2']) else 0
            b_head_landed, b_head_atmpted = parse_stat_value(row['Head_2'])
            b_body_landed, b_body_atmpted = parse_stat_value(row['Body_2'])
            b_leg_landed, b_leg_atmpted = parse_stat_value(row['Leg_2'])
            b_dist_landed, b_dist_atmpted = parse_stat_value(row['Distance_2'])
            b_clinch_landed, b_clinch_atmpted = parse_stat_value(row['Clinch_2'])
            b_ground_landed, b_ground_atmpted = parse_stat_value(row['Ground_2'])

            # BLUE accuracies
            b_sig_acc = calculate_accuracy(b_sig_landed, b_sig_atmpted)
            b_total_acc = calculate_accuracy(b_total_landed, b_total_atmpted)
            b_td_acc = calculate_accuracy(b_td_landed, b_td_atmpted)
            b_head_acc = calculate_accuracy(b_head_landed, b_head_atmpted)
            b_body_acc = calculate_accuracy(b_body_landed, b_body_atmpted)
            b_leg_acc = calculate_accuracy(b_leg_landed, b_leg_atmpted)
            b_dist_acc = calculate_accuracy(b_dist_landed, b_dist_atmpted)
            b_clinch_acc = calculate_accuracy(b_clinch_landed, b_clinch_atmpted)
            b_ground_acc = calculate_accuracy(b_ground_landed, b_ground_atmpted)
            total_sig_b = b_sig_landed
            b_lh_per = (b_head_landed / total_sig_b * 100) if total_sig_b else 0
            b_lb_per = (b_body_landed / total_sig_b * 100) if total_sig_b else 0
            b_ll_per = (b_leg_landed / total_sig_b * 100) if total_sig_b else 0
            b_ld_per = (b_dist_landed / total_sig_b * 100) if total_sig_b else 0
            b_lc_per = (b_clinch_landed / total_sig_b * 100) if total_sig_b else 0
            b_lg_per = (b_ground_landed / total_sig_b * 100) if total_sig_b else 0

            # WINNER - FIXED
            winner = row.get('Winner', 'Unknown')
            fighter_1_id = row.get('Fighter_1_Id', None)
            fighter_2_id = row.get('Fighter_2_Id', None)
            fighter_1_name = row.get('Fighter_1', '')
            fighter_2_name = row.get('Fighter_2', '')

            # Determine winner_id
            if winner == fighter_1_name:
                winner_id = fighter_1_id
            elif winner == fighter_2_name:
                winner_id = fighter_2_id
            else:
                winner_id = None

            # TIME FORMAT
            time_format = row['Time Format'] if pd.notna(row['Time Format']) else ''
            total_rounds = 5 if '5 Rnd' in time_format else 3

            # BUILD ROW
            transformed_row = {
                'date': fight_date,
                'location': row['Location'],
                'fight_id': row['Fight_Id'],
                'event_id': row.get('Event_Id', ''),
                'event_name': row.get('Event_Name', ''),
                'division': row['Weight_Class'],
                'title_fight': 1 if 'Title' in row.get('Weight_Class', '') else 0,
                'method': row['Method'],
                'finish_round': int(row['Round']) if pd.notna(row['Round']) else None,
                'match_time_sec': parse_time_to_seconds(row['Fight_Time']) if pd.notna(row['Fight_Time']) else 0,
                'total_rounds': total_rounds,
                'referee': row['Referee'] if pd.notna(row['Referee']) else '',

                # RED
                'r_name': row['Fighter_1'], 'r_id': row.get('Fighter_1_Id', None),
                'r_kd': r_kd, 'r_sig_str_landed': r_sig_landed, 'r_sig_str_atmpted': r_sig_atmpted,
                'r_sig_str_acc': r_sig_acc,
                'r_total_str_landed': r_total_landed, 'r_total_str_atmpted': r_total_atmpted,
                'r_total_str_acc': r_total_acc,
                'r_td_landed': r_td_landed, 'r_td_atmpted': r_td_atmpted, 'r_td_acc': r_td_acc,
                'r_sub_att': r_sub_att, 'r_ctrl': r_ctrl, 'r_head_landed': r_head_landed,
                'r_head_atmpted': r_head_atmpted, 'r_head_acc': r_head_acc,
                'r_body_landed': r_body_landed, 'r_body_atmpted': r_body_atmpted, 'r_body_acc': r_body_acc,
                'r_leg_landed': r_leg_landed, 'r_leg_atmpted': r_leg_atmpted, 'r_leg_acc': r_leg_acc,
                'r_dist_landed': r_dist_landed, 'r_dist_atmpted': r_dist_atmpted, 'r_dist_acc': r_dist_acc,
                'r_clinch_landed': r_clinch_landed, 'r_clinch_atmpted': r_clinch_atmpted, 'r_clinch_acc': r_clinch_acc,
                'r_ground_landed': r_ground_landed, 'r_ground_atmpted': r_ground_atmpted, 'r_ground_acc': r_ground_acc,
                'r_landed_head_per': r_lh_per, 'r_landed_body_per': r_lb_per, 'r_landed_leg_per': r_ll_per,
                'r_landed_dist_per': r_ld_per, 'r_landed_clinch_per': r_lc_per, 'r_landed_ground_per': r_lg_per,

                # RED BIO
                'r_nick_name': row.get('Fighter_1_nick_name', None), 'r_wins': row.get('Fighter_1_wins', None),
                'r_losses': row.get('Fighter_1_losses', None), 'r_draws': row.get('Fighter_1_draws', None),
                'r_height': convert_height_to_cm(row.get('Fighter_1_height')),
                'r_weight': convert_weight_to_kg(row.get('Fighter_1_weight')),
                'r_reach': convert_reach_to_cm(row.get('Fighter_1_reach')),
                'r_stance': row.get('Fighter_1_stance', None), 'r_dob': parse_date(row.get('Fighter_1_dob')),
                'r_splm': row.get('Fighter_1_splm', None),
                'r_str_acc': row.get('Fighter_1_str_acc', None), 'r_sapm': row.get('Fighter_1_sapm', None),
                'r_str_def': row.get('Fighter_1_str_def', None),
                'r_td_avg': row.get('Fighter_1_td_avg', None), 'r_td_avg_acc': row.get('Fighter_1_td_avg_acc', None),
                'r_td_def': row.get('Fighter_1_td_def', None), 'r_sub_avg': row.get('Fighter_1_sub_avg', None),

                # BLUE
                'b_name': row['Fighter_2'], 'b_id': row.get('Fighter_2_Id', None),
                'b_kd': b_kd, 'b_sig_str_landed': b_sig_landed, 'b_sig_str_atmpted': b_sig_atmpted,
                'b_sig_str_acc': b_sig_acc,
                'b_total_str_landed': b_total_landed, 'b_total_str_atmpted': b_total_atmpted,
                'b_total_str_acc': b_total_acc,
                'b_td_landed': b_td_landed, 'b_td_atmpted': b_td_atmpted, 'b_td_acc': b_td_acc,
                'b_sub_att': b_sub_att, 'b_ctrl': b_ctrl, 'b_head_landed': b_head_landed,
                'b_head_atmpted': b_head_atmpted, 'b_head_acc': b_head_acc,
                'b_body_landed': b_body_landed, 'b_body_atmpted': b_body_atmpted, 'b_body_acc': b_body_acc,
                'b_leg_landed': b_leg_landed, 'b_leg_atmpted': b_leg_atmpted, 'b_leg_acc': b_leg_acc,
                'b_dist_landed': b_dist_landed, 'b_dist_atmpted': b_dist_atmpted, 'b_dist_acc': b_dist_acc,
                'b_clinch_landed': b_clinch_landed, 'b_clinch_atmpted': b_clinch_atmpted, 'b_clinch_acc': b_clinch_acc,
                'b_ground_landed': b_ground_landed, 'b_ground_atmpted': b_ground_atmpted, 'b_ground_acc': b_ground_acc,
                'b_landed_head_per': b_lh_per, 'b_landed_body_per': b_lb_per, 'b_landed_leg_per': b_ll_per,
                'b_landed_dist_per': b_ld_per, 'b_landed_clinch_per': b_lc_per, 'b_landed_ground_per': b_lg_per,

                # BLUE BIO
                'b_nick_name': row.get('Fighter_2_nick_name', None), 'b_wins': row.get('Fighter_2_wins', None),
                'b_losses': row.get('Fighter_2_losses', None), 'b_draws': row.get('Fighter_2_draws', None),
                'b_height': convert_height_to_cm(row.get('Fighter_2_height')),
                'b_weight': convert_weight_to_kg(row.get('Fighter_2_weight')),
                'b_reach': convert_reach_to_cm(row.get('Fighter_2_reach')),
                'b_stance': row.get('Fighter_2_stance', None), 'b_dob': parse_date(row.get('Fighter_2_dob')),
                'b_splm': row.get('Fighter_2_splm', None),
                'b_str_acc': row.get('Fighter_2_str_acc', None), 'b_sapm': row.get('Fighter_2_sapm', None),
                'b_str_def': row.get('Fighter_2_str_def', None),
                'b_td_avg': row.get('Fighter_2_td_avg', None), 'b_td_avg_acc': row.get('Fighter_2_td_avg_acc', None),
                'b_td_def': row.get('Fighter_2_td_def', None), 'b_sub_avg': row.get('Fighter_2_sub_avg', None),

                'winner': winner, 'winner_id': winner_id
            }

            transformed_rows.append(transformed_row)

        except Exception as e:
            print(f"Error row {idx}: {e}")
            continue

    return pd.DataFrame(transformed_rows)


# --- MAIN ---
if __name__ == "__main__":
    raw_df = pd.read_csv("Uncleaned/UFC_updated_raw.csv")
    print("Transforming new fights...")
    transformed_df = transform_to_ufc_clean_format(raw_df)

    transformed_df['date'] = pd.to_datetime(transformed_df['date'], errors='coerce')

    existing_df = pd.read_csv("csv/UFC_clean.csv")

    if 'date' in existing_df.columns:
        existing_df['date'] = pd.to_datetime(existing_df['date'], errors='coerce')
    else:
        existing_df['date'] = pd.NaT

    combined_df = pd.concat([existing_df, transformed_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['fight_id'], keep='first')

    combined_df = combined_df.sort_values('date', ascending=False)

    combined_df.to_csv("Uncleaned/UFC.csv", index=False)

    print("Updated CSV saved")
    print("New fights added:", len(transformed_df))
    print("Total fights in UFC.csv:", len(combined_df))