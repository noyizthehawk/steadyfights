import requests
import bs4
import pandas as pd
from datetime import datetime
import time


def cached_request(url):
    """Simple request wrapper"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    time.sleep(1)
    return response.text


def extract_cells(table, fight_dict={}, cols_to_ignore=0):
    """Extract cells from fight stats tables"""
    cells = table.select('td')
    del cells[:cols_to_ignore]

    headers = [formatted_header.title() for header in table.select('th') for formatted_header in (
        f"{header.get_text(strip=True)}_1", f"{header.get_text(strip=True)}_2")]
    del headers[:cols_to_ignore * 2]

    cells = [s for cell in cells for s in cell.stripped_strings]

    for header, cell in zip(headers, cells):
        fight_dict[header] = cell


def scrape_fighter_profile(fighter_id):
    """Scrape career stats from fighter profile page"""
    if not fighter_id:
        return {}

    fighter_url = f"http://ufcstats.com/fighter-details/{fighter_id}"

    try:
        fighter_html = cached_request(fighter_url)
        soup = bs4.BeautifulSoup(fighter_html, 'html.parser')

        fighter_stats = {}

        name_elem = soup.select_one('.b-content__title-highlight')
        if name_elem:
            nickname = name_elem.get_text(strip=True).replace('"', '')
            fighter_stats['nick_name'] = nickname

        record_elem = soup.select_one('.b-content__title-record')
        if record_elem:
            record_text = record_elem.get_text(strip=True)
            if ':' in record_text:
                record = record_text.split(':')[1].strip()
                parts = record.split('-')
                if len(parts) >= 3:
                    fighter_stats['wins'] = parts[0].strip()
                    fighter_stats['losses'] = parts[1].strip()
                    fighter_stats['draws'] = parts[2].strip()

        bio_list = soup.select('.b-list__box-list-item')

        for item in bio_list:
            label = item.get_text(strip=True).lower()

            if ':' in label:
                parts = label.split(':', 1)
                field_name = parts[0].strip()
                field_value = parts[1].strip() if len(parts) > 1 else ''

                if 'height' in field_name:
                    fighter_stats['height'] = field_value
                elif 'weight' in field_name:
                    fighter_stats['weight'] = field_value
                elif 'reach' in field_name:
                    fighter_stats['reach'] = field_value
                elif 'stance' in field_name:
                    fighter_stats['stance'] = field_value
                elif 'dob' in field_name:
                    fighter_stats['dob'] = field_value

        stat_boxes = soup.select('.b-list__info-box')

        for box in stat_boxes:
            label_elem = box.select_one('.b-list__info-box-title')
            value_elem = box.select_one('.b-list__info-box-value')

            if label_elem and value_elem:
                label = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)

                if 'slpm' in label:
                    fighter_stats['splm'] = value
                elif 'str. acc.' in label:
                    fighter_stats['str_acc'] = value
                elif 'sapm' in label:
                    fighter_stats['sapm'] = value
                elif 'str. def' in label:
                    fighter_stats['str_def'] = value
                elif 'td avg.' in label and 'def' not in label:
                    fighter_stats['td_avg'] = value
                elif 'td acc.' in label:
                    fighter_stats['td_avg_acc'] = value
                elif 'td def.' in label:
                    fighter_stats['td_def'] = value
                elif 'sub. avg.' in label:
                    fighter_stats['sub_avg'] = value

        return fighter_stats

    except Exception as e:
        print(f"Error scraping fighter profile {fighter_id}: {e}")
        return {}


def parse_fight_details(fight_html):
    """Parse detailed fight stats from fight detail page"""
    fight_dict = {}

    soup = bs4.BeautifulSoup(fight_html, 'html.parser')

    fighters_result_div = soup.select('.b-fight-details__person')

    fighter_1_id = None
    fighter_2_id = None
    fighter_1_name = None
    fighter_2_name = None

    if len(fighters_result_div) >= 2:
        fighter_1_link = fighters_result_div[0].select_one('a.b-link.b-fight-details__person-link')
        if fighter_1_link and fighter_1_link.has_attr('href'):
            fighter_1_id = fighter_1_link['href'].split('/')[-1]
            fighter_1_name = fighter_1_link.get_text(strip=True)

        result_1_elem = fighters_result_div[0].select_one('.b-fight-details__person-status')
        result_1 = result_1_elem.get_text(strip=True) if result_1_elem else ''
        fight_dict['Result_1'] = result_1

        fighter_2_link = fighters_result_div[1].select_one('a.b-link.b-fight-details__person-link')
        if fighter_2_link and fighter_2_link.has_attr('href'):
            fighter_2_id = fighter_2_link['href'].split('/')[-1]
            fighter_2_name = fighter_2_link.get_text(strip=True)

        result_2_elem = fighters_result_div[1].select_one('.b-fight-details__person-status')
        result_2 = result_2_elem.get_text(strip=True) if result_2_elem else ''
        fight_dict['Result_2'] = result_2

        if 'W' in result_1:
            fight_dict['Winner'] = fighter_1_name
        elif 'W' in result_2:
            fight_dict['Winner'] = fighter_2_name
        elif 'D' in result_1 or 'D' in result_2:
            fight_dict['Winner'] = 'Draw'
        elif 'NC' in result_1 or 'NC' in result_2:
            fight_dict['Winner'] = 'No Contest'
        else:
            fight_dict['Winner'] = None

    fight_dict['Fighter_1_Id'] = fighter_1_id
    fight_dict['Fighter_2_Id'] = fighter_2_id
    fight_dict['Fighter_1_Name'] = fighter_1_name
    fight_dict['Fighter_2_Name'] = fighter_2_name

    fight_details_text = soup.select_one('.b-fight-details__content')
    if fight_details_text:
        paras = fight_details_text.find_all('p')

        if paras:
            first_para = paras[0]
            first_para_i_tags = first_para.find_all('i', recursive=False)
            if len(first_para_i_tags) >= 4:
                fight_dict['Time Format'] = first_para_i_tags[3].get_text(
                    strip=True).split(':')[1] if ':' in first_para_i_tags[3].get_text(strip=True) else ''
            if len(first_para_i_tags) >= 5:
                fight_dict['Referee'] = first_para_i_tags[4].get_text(strip=True).split(':')[
                    1] if ':' in first_para_i_tags[4].get_text(strip=True) else ''

            if len(paras) >= 2:
                second_para = paras[1]
                i_tag = second_para.select_one('i')
                if i_tag:
                    i_tag.decompose()
                fight_dict['Method Details'] = second_para.get_text(strip=True)

    tables_soup = soup.select('table')
    if tables_soup and len(tables_soup) >= 3:
        totals_table = tables_soup[0]
        extract_cells(totals_table, fight_dict, cols_to_ignore=1)

        sig_str_table = tables_soup[2]
        extract_cells(sig_str_table, fight_dict, cols_to_ignore=3)

    return fight_dict


def get_fights_data(cells):
    """Extract fight data from event page table row"""
    result_flag = cells[0].get_text(strip=True)
    fighters = [a.get_text(strip=True) for a in cells[1].select("a.b-link")]
    kd = [p.get_text(strip=True) for p in cells[2].select("p")]
    strikes = [p.get_text(strip=True) for p in cells[3].select("p")]
    td = [p.get_text(strip=True) for p in cells[4].select("p")]
    sub = [p.get_text(strip=True) for p in cells[5].select("p")]
    weight_class = cells[6].get_text(strip=True)
    method = " ".join([p.get_text(strip=True)
                       for p in cells[7].select("p") if p.get_text(strip=True)])
    round_num = cells[8].get_text(strip=True)
    fight_time = cells[9].get_text(strip=True)

    return [result_flag, *fighters, *kd, *strikes, *td, *sub, weight_class, method, round_num, fight_time]


def get_event_data(event):
    """Extract event metadata"""
    first_td = event.select_one('td.b-statistics__table-col')
    event_link = first_td.select_one('a.b-link')
    event_name = event_link.get_text(strip=True)
    event_id = event_link['href'].split('/')[-1]
    event_url = event_link['href']
    event_date = first_td.select_one('span.b-statistics__date').get_text(strip=True)
    location = event.select_one('td.b-statistics__table-col_style_big-top-padding').get_text(strip=True)

    return {
        'event_id': event_id,
        'event_name': event_name,
        'event_date': event_date,
        'event_url': event_url,
        'location': location
    }


def scrape_new_fights(csv_path, output_path=None):
    """Main function: scrape fights newer than last fight in CSV"""

    if output_path is None:
        output_path = csv_path.replace('.csv', '_updated.csv')

    print("Loading existing CSV...")
    existing_df = pd.read_csv(csv_path)
    existing_df['date'] = pd.to_datetime(existing_df['date'])
    last_date = existing_df['date'].max()
    print(f"Last fight in CSV: {last_date.date()}\n")

    print("Fetching events list...")
    events_html = cached_request("http://ufcstats.com/statistics/events/completed?page=all")
    events_soup = bs4.BeautifulSoup(events_html, 'html.parser')
    events_rows = events_soup.select('table tbody tr.b-statistics__table-row')
    events_rows.pop(0)

    new_events = []
    for event in events_rows:
        event_data = get_event_data(event)
        event_date = datetime.strptime(event_data['event_date'], '%B %d, %Y')

        if event_date > last_date:
            event_data['event_date_parsed'] = event_date
            new_events.append(event_data)
            print(f"  Found: {event_data['event_name']} ({event_date.date()})")
        else:
            break

    if not new_events:
        print("\nNo new events found. Data is up to date!")
        return

    print(f"\nTotal new events to scrape: {len(new_events)}\n")

    fights_list = []

    for event_data in new_events:
        print(f"\nScraping: {event_data['event_name']}")

        event_html = cached_request(event_data['event_url'])
        event_soup = bs4.BeautifulSoup(event_html, "html.parser")

        fights = event_soup.select("table.b-fight-details__table tbody tr.b-fight-details__table-row")

        print(f"   Found {len(fights)} fights")

        for fight_row in fights:
            try:
                cells = fight_row.select('td')
                if len(cells) == 0:
                    continue

                fight_info = get_fights_data(cells)
                fight_id = fight_row['data-link'].split('/')[-1]
                fight_details_link = fight_row['data-link']

                fight_details_html = cached_request(fight_details_link)
                fight_dict = parse_fight_details(fight_details_html)

                fight_dict['Fight_Id'] = fight_id
                fight_dict['Event_Id'] = event_data['event_id']
                fight_dict['Event_Name'] = event_data['event_name']
                fight_dict['Date'] = datetime.strptime(event_data['event_date'], '%B %d, %Y').strftime('%Y-%m-%d')
                fight_dict['Location'] = event_data['location']

                basic_headers = ["Win/No Contest/Draw", "Fighter_1", "Fighter_2", "KD_1", "KD_2",
                                 "STR_1", "STR_2", "TD_1", "TD_2", "SUB_1", "SUB_2",
                                 "Weight_Class", "Method", "Round", "Fight_Time"]

                for header, value in zip(basic_headers, fight_info):
                    fight_dict[header] = value

                fighter_1_id = fight_dict.get('Fighter_1_Id')
                fighter_2_id = fight_dict.get('Fighter_2_Id')

                print(f"       Fetching fighter profiles...")
                fighter_1_profile = scrape_fighter_profile(fighter_1_id)
                fighter_2_profile = scrape_fighter_profile(fighter_2_id)

                for key, value in fighter_1_profile.items():
                    fight_dict[f'Fighter_1_{key}'] = value

                for key, value in fighter_2_profile.items():
                    fight_dict[f'Fighter_2_{key}'] = value

                fights_list.append(fight_dict)
                print(f"     Completed: {fight_dict['Fighter_1']} vs {fight_dict['Fighter_2']}")

            except Exception as e:
                print(f"     Error scraping fight: {e}")
                continue

    if not fights_list:
        print("\nNo new fights scraped")
        return

    print(f"\nProcessing {len(fights_list)} new fights...")
    new_fights_df = pd.DataFrame(fights_list)

    new_fights_df.to_csv(output_path.replace('.csv', '_raw.csv'), index=False)
    print(f"Raw new fights saved to: {output_path.replace('.csv', '_raw.csv')}")
    print(f"\nNext step: Run transform.py to convert to UFC_clean format")

    return new_fights_df


if __name__ == "__main__":
    scrape_new_fights(
        csv_path="csv/UFC_clean.csv",
        output_path="Uncleaned/UFC_updated.csv"
    )