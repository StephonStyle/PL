"""
Fetch Chinese player names from Wikipedia for all PL teams.
Uses hardcoded section numbers + auto-detect fallback.
"""
import json, os, time, re, sys
import urllib.request, urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
OUTPUT = os.path.join(DATA_DIR, 'chinese_names.json')

# (page_title, section_number_or_None_for_auto)
TEAMS = [
    ('阿森纳足球俱乐部', '26'),
    ('阿士東維拉足球會', None),      # Aston Villa - need section
    ('伯恩茅斯足球俱乐部', '14'),
    ('布伦特福德足球俱乐部', '14'),
    ('白禮頓足球會', None),            # Brighton - need section
    ('切尔西足球俱乐部', '36'),
    ('水晶宫足球俱乐部', '10'),
    ('埃弗顿足球俱乐部', '6'),
    ('富勒姆足球俱乐部', '23'),
    ('伊普斯威奇足球俱乐部', None),     # Ipswich - need section
    ('莱斯特城足球俱乐部', '26'),
    ('利物浦足球俱乐部', '31'),
    ('曼彻斯特城足球俱乐部', None),     # Man City - need section
    ('曼彻斯特联足球俱乐部', None),     # Man Utd - need section
    ('纽卡斯尔联足球俱乐部', None),     # Newcastle - need section
    ('诺丁汉森林足球俱乐部', None),     # Nott'm Forest - need section
    ('南安普顿足球俱乐部', None),       # Southampton - need section
    ('托特纳姆热刺足球俱乐部', None),   # Spurs - need section
    ('西汉姆联足球俱乐部', '16'),
    ('狼队足球俱乐部', None),           # Wolves - need section
]

API = 'https://zh.wikipedia.org/w/api.php'
HEADERS = {'User-Agent': 'PL-Database/1.0 (https://github.com/StephonStyle/PL)'}

def api_call(params):
    params['format'] = 'json'
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f'  Rate limited, waiting 10s...', flush=True)
                time.sleep(10)
            else:
                print(f'  HTTP {e.code}, retry {attempt+1}', flush=True)
                time.sleep(5)
        except Exception as e:
            print(f'  Error: {e}, retry {attempt+1}', flush=True)
            time.sleep(5)
    return None

def find_section(page):
    """Auto-find the squad section for a page."""
    data = api_call({'action': 'parse', 'page': page, 'prop': 'sections'})
    if not data or 'parse' not in data:
        return None
    for s in data['parse'].get('sections', []):
        line = s.get('line', '')
        if ('球员名单' in line or '球員名單' in line) and ('2025' in line or '2026' in line):
            return s['index']
    for s in data['parse'].get('sections', []):
        line = s.get('line', '')
        if '球员名单' in line or '球員名單' in line:
            return s['index']
    for s in data['parse'].get('sections', []):
        line = s.get('line', '')
        if ('现役球员' in line or '現役球員' in line) and ('2025' in line or '2026' in line):
            return s['index']
    return None

def extract_names(wikitext):
    names = {}
    for line in wikitext.split('\n'):
        line = line.strip()
        if not line or line.startswith('!') or line.startswith('|}') or line.startswith('|-'):
            continue
        en, cn = None, None
        m = re.search(r'\[\[([^|\]]+)\|[^]]*\]\]\s*（([^）]+)）', line)
        if m:
            en = m.group(2).strip()
            hans = re.search(r'zh-hans:([^;]+)', line)
            cn = hans.group(1).strip() if hans else m.group(1).strip()
        else:
            m = re.search(r'\{\{le\|([^|]+)\|([^}]+)\}\}\s*（([^）]+)）', line)
            if m:
                cn = m.group(1).strip()
                en = m.group(3).strip()
            else:
                m = re.search(r'\[\[([^\]]+)\]\]\s*（([^）]+)）', line)
                if m:
                    cn = m.group(1).strip()
                    en = m.group(2).strip()
        if en and cn and len(en) > 2:
            en_clean = re.sub(r'\s*[（(][^）)]*[）)]', '', en).strip()
            names[en_clean] = cn
    return names

def main():
    all_names = {}
    for page, section in TEAMS:
        print(f'{page}...', flush=True)
        time.sleep(1.5)

        if section is None:
            section = find_section(page)
            if section:
                print(f'  Auto-detected section {section}', flush=True)
            else:
                print(f'  SKIPPED (no section)', flush=True)
                continue
            time.sleep(1.5)

        wikitext = None
        for sec in [section, f'{section}.1']:
            data = api_call({
                'action': 'parse', 'page': page,
                'section': str(sec), 'prop': 'wikitext', 'disabletoc': '1'
            })
            if data and 'parse' in data:
                wikitext = (wikitext or '') + data['parse']['wikitext']['*']

        if wikitext:
            names = extract_names(wikitext)
            all_names.update(names)
            print(f'  -> {len(names)} players', flush=True)
        else:
            print(f'  -> No content', flush=True)

    print(f'\nTotal: {len(all_names)} Chinese names', flush=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(all_names, f, ensure_ascii=False, indent=2)
    print(f'Saved to {OUTPUT}', flush=True)

if __name__ == '__main__':
    main()
