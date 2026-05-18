"""
Premier League Data Crawler — transfermarkt.co.uk
Features: checkpoint/resume, rate limiting, Unicode-safe
"""

import requests, json, os, time, re, sys
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CHECKPOINT = os.path.join(DATA_DIR, '_checkpoint.json')
RATE = 3.5

# Premier League 2024/25 teams with verified Transfermarkt IDs
TEAMS = [
    {'id': '11', 'name': 'Arsenal'},
    {'id': '405', 'name': 'Aston Villa'},
    {'id': '989', 'name': 'Bournemouth'},
    {'id': '1148', 'name': 'Brentford'},
    {'id': '1237', 'name': 'Brighton'},
    {'id': '631', 'name': 'Chelsea'},
    {'id': '873', 'name': 'Crystal Palace'},
    {'id': '29', 'name': 'Everton'},
    {'id': '931', 'name': 'Fulham'},
    {'id': '677', 'name': 'Ipswich'},
    {'id': '1003', 'name': 'Leicester'},
    {'id': '31', 'name': 'Liverpool'},
    {'id': '281', 'name': 'Man City'},
    {'id': '985', 'name': 'Man United'},
    {'id': '762', 'name': 'Newcastle'},
    {'id': '703', 'name': "Nott'm Forest"},
    {'id': '180', 'name': 'Southampton'},
    {'id': '148', 'name': 'Spurs'},
    {'id': '379', 'name': 'West Ham'},
    {'id': '543', 'name': 'Wolves'},
]

def log(msg):
    safe = msg.encode('ascii', errors='replace').decode('ascii')
    print(f"[{time.strftime('%H:%M:%S')}] {safe}", flush=True)

def get(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                time.sleep(RATE)
                return r.text
            elif r.status_code == 429:
                log(f"Rate limited, waiting 60s...")
                time.sleep(60)
            else:
                log(f"HTTP {r.status_code} for {url}, retry {i+1}")
                time.sleep(RATE * 2)
        except Exception as e:
            log(f"Request error: {e}, retry {i+1}")
            time.sleep(10)
    return None

def save_checkpoint(data):
    with open(CHECKPOINT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# ==================== STEP 1: Crawl team squads ====================
def crawl_squads():
    log("=== Step 1: Crawling team squads ===")
    cp = load_checkpoint()
    done = cp.get('done_squads', [])

    for team in TEAMS:
        tid = team['id']
        if tid in done:
            log(f"Skipping {team['name']} (already done)")
            continue

        log(f"Fetching squad: {team['name']} (ID: {tid})")
        html = get(f'https://www.transfermarkt.co.uk/verein/startseite/verein/{tid}')
        players = []

        if html:
            soup = BeautifulSoup(html, 'lxml')
            # Squad table rows
            for row in soup.select('table.wp tbody tr, table.items tbody tr'):
                tds = row.select('td')
                if len(tds) < 8:
                    # Check if it's a non-player row (filter, heading, etc.)
                    continue

                # td[3] = player name with link
                name_link = tds[3].select_one('a[href*="/profil/spieler/"]')
                if not name_link:
                    continue
                href = name_link.get('href', '')
                m = re.search(r'/spieler/(\d+)', href)
                if not m:
                    continue
                pid = m.group(1)
                name = name_link.get_text(strip=True)
                if not name or len(name) < 2:
                    continue

                # Filter out recommended players from other teams.
                # Real squad: td[1] has 1 link (player profile).
                # Recommeded: td[1] has extra team links.
                if len(tds[1].select('a')) > 1:
                    continue

                # td[0] = shirt number
                num = tds[0].get_text(strip=True)

                # td[4] = position
                pos = tds[4].get_text(strip=True)

                # td[5] = "15/09/1995 (30)" — birth date + age
                birth_info = tds[5].get_text(strip=True)
                age = ''
                m_age = re.search(r'\((\d+)\)', birth_info)
                if m_age:
                    age = m_age.group(1)

                # td[6] = nationality flags
                nations = []
                for flag in tds[6].select('img.flaggenrahmen, img.flaggen'):
                    alt = flag.get('alt', '')
                    if alt:
                        nations.append(alt)

                # td[7] = market value
                mv = tds[7].get_text(strip=True)

                players.append({
                    'id': pid,
                    'name': name,
                    'position': pos,
                    'number': num,
                    'age': age,
                    'nationality': nations,
                    'market_value': mv,
                })

        team['players'] = players
        team['player_count'] = len(players)
        log(f"  -> {len(players)} players")

        with open(os.path.join(DATA_DIR, f'squad_{tid}.json'), 'w', encoding='utf-8') as f:
            json.dump(players, f, ensure_ascii=False, indent=2)

        done.append(tid)
        total = sum(t.get('player_count', 0) for t in TEAMS if t['id'] in done)
        save_checkpoint({'step': 'squads', 'done_squads': done, 'total_players': total})

    # Merge data into teams file
    final_teams = []
    for team in TEAMS:
        sf = os.path.join(DATA_DIR, f'squad_{team["id"]}.json')
        if os.path.exists(sf):
            with open(sf, 'r', encoding='utf-8') as f:
                team['players'] = json.load(f)
                team['player_count'] = len(team['players'])
        final_teams.append(team)

    with open(os.path.join(DATA_DIR, 'teams.json'), 'w', encoding='utf-8') as f:
        json.dump(final_teams, f, ensure_ascii=False, indent=2)

    total_players = sum(t.get('player_count', 0) for t in final_teams)
    log(f"Squad crawl complete. {len(final_teams)} teams, {total_players} players")
    save_checkpoint({'step': 'squads_done', 'total_players': total_players})
    return total_players

# ==================== STEP 2: Crawl player details ====================
def crawl_player_details():
    log("=== Step 2: Crawling player details ===")
    cp = load_checkpoint()
    done_ids = cp.get('done_details', [])

    # Collect all players
    all_players = []
    for team in TEAMS:
        sf = os.path.join(DATA_DIR, f'squad_{team["id"]}.json')
        if os.path.exists(sf):
            with open(sf, 'r', encoding='utf-8') as f:
                squad = json.load(f)
                for p in squad:
                    p['team_id'] = team['id']
                    p['team_name'] = team['name']
                all_players.extend(squad)

    total = len(all_players)
    log(f"Total: {total} players, {len(done_ids)} already done")

    for i, player in enumerate(all_players):
        pid = player['id']
        if pid in done_ids:
            continue

        log(f"[{i+1}/{total}] {player['name']}")
        html = get(f'https://www.transfermarkt.co.uk/spieler/profil/spieler/{pid}')

        if html:
            soup = BeautifulSoup(html, 'lxml')

            # Info table (div.info-table with span pairs)
            info_table = soup.select_one('div.info-table')
            if info_table:
                spans = info_table.select('span.info-table__content')
                for j in range(0, len(spans) - 1, 2):
                    label = spans[j].get_text(strip=True).lower()
                    value = spans[j + 1].get_text(strip=True)
                    if 'date of birth' in label:
                        m_dob = re.search(r'(\d{2}/\d{2}/\d{4})', value)
                        if m_dob:
                            player['birth_date'] = m_dob.group(1)
                    elif 'place of birth' in label:
                        player['birth_place'] = value
                    elif 'height' in label:
                        player['height'] = value
                    elif 'citizenship' in label:
                        flags = spans[j + 1].select('img.flaggenrahmen')
                        player['nationality'] = [img.get('alt', '') for img in flags if img.get('alt')]
                        if not player['nationality']:
                            player['nationality'] = [value.split()[-1]]
                    elif 'position' in label and 'player agent' not in label:
                        player['position'] = value
                    elif 'foot' in label:
                        player['foot'] = value
                    elif 'player agent' in label:
                        player['agent'] = value
                    elif 'current club' in label:
                        player['club'] = value
                    elif 'joined' in label:
                        player['joined'] = value
                    elif 'contract expires' in label:
                        player['contract_expiry'] = value
                    elif 'name in home' in label:
                        player['full_name'] = value

            # Market value
            mv_el = soup.select_one('a.data-header__market-value-wrapper')
            if mv_el:
                last_update = mv_el.select_one('p.data-header__last-update')
                if last_update:
                    last_update.decompose()
                player['market_value'] = mv_el.get_text(strip=True)
        else:
            player['detail_error'] = True

        done_ids.append(pid)

        # Save every 20 players
        if len(done_ids) % 20 == 0:
            with open(os.path.join(DATA_DIR, 'players_details.json'), 'w', encoding='utf-8') as f:
                json.dump(all_players, f, ensure_ascii=False, indent=2)
            save_checkpoint({
                'step': 'details',
                'done_details': done_ids,
                'progress': f'{len(done_ids)}/{total}'
            })

    # Final save
    with open(os.path.join(DATA_DIR, 'players_details.json'), 'w', encoding='utf-8') as f:
        json.dump(all_players, f, ensure_ascii=False, indent=2)

    save_checkpoint({'step': 'done', 'total_players': len(all_players)})

    # Build summary
    summary = {
        'league': 'Premier League',
        'season': '2024/2025',
        'teams': [{'id': t['id'], 'name': t['name'], 'player_count': t.get('player_count', 0)} for t in TEAMS],
        'total_players': len(all_players),
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(os.path.join(DATA_DIR, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log(f"ALL DONE! {len(all_players)} players saved.")

# ==================== MAIN ====================
def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    cp = load_checkpoint()
    step = cp.get('step', '')
    log(f"Resuming from checkpoint: step={step}")

    if step in ('', 'squads') or 'squads_done' not in str(step):
        total = crawl_squads()
        log(f"Teams done. Ready for player details.")
    else:
        log("Squad data already complete.")

    if step != 'done':
        crawl_player_details()
    else:
        log("All data already complete!")

    log("Script finished.")

if __name__ == '__main__':
    main()
