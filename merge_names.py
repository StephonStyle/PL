"""
Merge Chinese names into players_details.json.
Matches by player name (with fallback for name variations).
"""
import json, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Load data
with open(os.path.join(DATA_DIR, 'players_details.json'), encoding='utf-8') as f:
    players = json.load(f)

try:
    with open(os.path.join(DATA_DIR, 'chinese_names.json'), encoding='utf-8') as f:
        cn_map = json.load(f)
except:
    cn_map = {}

print(f'Players: {len(players)}, Chinese names: {len(cn_map)}', flush=True)

# Clean cn_map: remove entries with '' prefixes (historical Chelsea players)
cn_map = {k: v for k, v in cn_map.items() if not k.startswith("'")}
print(f'After cleaning: {len(cn_map)} Chinese names', flush=True)

# Build name lookup helper
def normalize(name):
    """Normalize a name for comparison."""
    name = name.lower().strip()
    # Remove accents
    name = name.replace('ø', 'o').replace('Ø', 'O').replace('ö', 'o').replace('Ö', 'O')
    name = name.replace('é', 'e').replace('É', 'E').replace('ü', 'u').replace('Ü', 'U')
    name = name.replace('á', 'a').replace('Á', 'A').replace('í', 'i').replace('Í', 'I')
    name = name.replace('ñ', 'n').replace('ç', 'c').replace('ş', 's')
    return name

def get_surname(name):
    """Get the last name (surname) from a full name."""
    parts = name.split()
    return parts[-1].lower().strip(".'") if parts else ''

# Build surname index from cn_map
surname_map = {}
for en_name, cn in cn_map.items():
    surname = get_surname(en_name)
    if surname not in surname_map:
        surname_map[surname] = []
    surname_map[surname].append((en_name, cn))

# Match each player
matched = 0
by_surname = 0
for p in players:
    pname = p.get('name', '')
    norm = normalize(pname)
    surname = get_surname(pname)

    # 1. Exact match
    if pname in cn_map:
        p['cn_name'] = cn_map[pname]
        matched += 1
        continue

    # 2. Normalized match
    found = False
    for en_name, cn in cn_map.items():
        if normalize(en_name) == norm:
            p['cn_name'] = cn
            matched += 1
            found = True
            break
    if found:
        continue

    # 3. Surname match (if only one option)
    if surname in surname_map and len(surname_map[surname]) == 1:
        en_name, cn = surname_map[surname][0]
        p['cn_name'] = cn
        by_surname += 1
        matched += 1
        continue

    # 4. Surname match (check if surname appears in the Chinese name entry's full name)
    candidates = [item for item in cn_map.items()
                  if surname in normalize(item[0])]
    if len(candidates) == 1:
        p['cn_name'] = candidates[0][1]
        by_surname += 1
        matched += 1
        continue

print(f'Matched: {matched} (exact+normalized={matched-by_surname}, by_surname={by_surname})', flush=True)
print(f'Unmatched: {len(players) - matched}', flush=True)

# Save updated players
with open(os.path.join(DATA_DIR, 'players_details.json'), 'w', encoding='utf-8') as f:
    json.dump(players, f, ensure_ascii=False, indent=2)

print('Saved players_details.json with cn_name', flush=True)
